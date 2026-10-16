"""Session governance, MFA lifecycle, step-up, and security event ledger."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.auth.mfa import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_code,
    otpauth_uri,
    verify_totp,
)
from dogeapi.auth.passwords import verify_password
from dogeapi.models import AuthSession, Membership, Role, SecurityEvent, StaffAssignment, User, UserSecurityProfile
from dogeapi.settings import Settings


def request_context(request: Request) -> tuple[str | None, str | None]:
    forwarded = request.headers.get("x-forwarded-for")
    ip_address = forwarded.split(",", 1)[0].strip() if forwarded else (request.client.host if request.client else None)
    return ip_address, request.headers.get("user-agent", "")[:500] or None


def add_security_event(
    session: AsyncSession,
    *,
    event_type: str,
    outcome: str,
    description: str,
    user_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    auth_session_id: UUID | None = None,
    org_id: UUID | None = None,
    severity: str = "info",
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    session.add(
        SecurityEvent(
            org_id=org_id,
            user_id=user_id,
            actor_user_id=actor_user_id,
            session_id=auth_session_id,
            event_type=event_type,
            severity=severity,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
            event_metadata=metadata or {},
        )
    )


async def create_auth_session(
    session: AsyncSession,
    settings: Settings,
    user_id: UUID,
    request: Request,
    *,
    mfa_authenticated: bool,
) -> AuthSession:
    ip_address, user_agent = request_context(request)
    item = AuthSession(
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.now(UTC) + settings.jwt_refresh_expires,
        mfa_authenticated=mfa_authenticated,
    )
    session.add(item)
    await session.flush()
    add_security_event(
        session,
        event_type="LoginSucceeded",
        outcome="success",
        description="Authenticated session created",
        user_id=user_id,
        actor_user_id=user_id,
        auth_session_id=item.id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"mfa_authenticated": mfa_authenticated},
    )
    await session.flush()
    return item


async def is_privileged_user(db: AsyncSession, user_id: UUID) -> bool:
    privileged_membership = await db.scalar(
        select(Membership.user_id).where(
            Membership.user_id == user_id,
            Membership.role.in_({Role.OWNER, Role.ADMIN}),
        )
    )
    if privileged_membership is not None:
        return True
    privileged_assignment = await db.scalar(
        select(StaffAssignment.user_id).where(
            StaffAssignment.user_id == user_id,
            StaffAssignment.is_active,
            StaffAssignment.operational_role.in_(
                {"ops_admin", "branch_manager", "finance_manager", "compliance_officer", "security_admin"}
            ),
        )
    )
    return privileged_assignment is not None


async def get_active_session(db: AsyncSession, user_id: UUID, session_id: UUID, *, lock: bool = False) -> AuthSession:
    statement = select(AuthSession).where(
        AuthSession.id == session_id,
        AuthSession.user_id == user_id,
        AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > datetime.now(UTC),
    )
    if lock:
        statement = statement.with_for_update()
    item = await db.scalar(statement)
    if item is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or revoked")
    return item


async def list_sessions(db: AsyncSession, user_id: UUID) -> list[AuthSession]:
    return list(
        (
            await db.scalars(
                select(AuthSession)
                .where(AuthSession.user_id == user_id)
                .order_by(AuthSession.created_at.desc())
                .limit(100)
            )
        ).all()
    )


async def revoke_session(db: AsyncSession, actor: User, session_id: UUID, reason: str) -> AuthSession:
    item = await db.scalar(
        select(AuthSession).where(AuthSession.id == session_id, AuthSession.user_id == actor.id).with_for_update()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    now = datetime.now(UTC)
    if item.revoked_at is None:
        item.revoked_at = now
        item.revoked_by_user_id = actor.id
        item.revoke_reason = reason
        add_security_event(
            db,
            event_type="SessionRevoked",
            outcome="success",
            description="User session revoked",
            user_id=actor.id,
            actor_user_id=actor.id,
            auth_session_id=item.id,
            severity="medium",
            metadata={"reason": reason},
        )
    await db.flush()
    return item


async def get_profile(db: AsyncSession, user_id: UUID, *, lock: bool = False) -> UserSecurityProfile:
    statement = select(UserSecurityProfile).where(UserSecurityProfile.user_id == user_id)
    if lock:
        statement = statement.with_for_update()
    profile = await db.scalar(statement)
    if profile is None:
        profile = UserSecurityProfile(user_id=user_id)
        db.add(profile)
        await db.flush()
    return profile


async def begin_mfa_setup(
    db: AsyncSession, settings: Settings, user: User, password: str, request: Request
) -> tuple[str, str]:
    if user.password_hash is None or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Password verification failed")
    profile = await get_profile(db, user.id, lock=True)
    secret = generate_totp_secret()
    profile.totp_secret_ciphertext = encrypt_totp_secret(settings, secret)
    profile.mfa_enabled = False
    profile.recovery_code_hashes = []
    ip_address, user_agent = request_context(request)
    add_security_event(
        db,
        event_type="MfaSetupStarted",
        outcome="success",
        description="TOTP enrollment started",
        user_id=user.id,
        actor_user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.flush()
    return secret, otpauth_uri(secret, user.email)


async def activate_mfa(db: AsyncSession, settings: Settings, user: User, code: str, request: Request) -> list[str]:
    profile = await get_profile(db, user.id, lock=True)
    if not profile.totp_secret_ciphertext:
        raise HTTPException(status.HTTP_409_CONFLICT, "Start MFA setup first")
    secret = decrypt_totp_secret(settings, profile.totp_secret_ciphertext)
    if not verify_totp(secret, code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authenticator code")
    codes = generate_recovery_codes()
    profile.mfa_enabled = True
    profile.activated_at = datetime.now(UTC)
    profile.recovery_code_hashes = [hash_recovery_code(settings, item) for item in codes]
    profile.recovery_codes_generated_at = datetime.now(UTC)
    profile.failed_attempts = 0
    ip_address, user_agent = request_context(request)
    add_security_event(
        db,
        event_type="MfaActivated",
        outcome="success",
        description="TOTP MFA activated",
        user_id=user.id,
        actor_user_id=user.id,
        severity="medium",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.flush()
    return codes


async def verify_mfa(
    db: AsyncSession, settings: Settings, user_id: UUID, code: str | None, *, allow_recovery: bool = True
) -> bool:
    profile = await get_profile(db, user_id, lock=True)
    if not profile.mfa_enabled:
        return False
    now = datetime.now(UTC)
    if profile.locked_until and profile.locked_until > now:
        raise HTTPException(status.HTTP_423_LOCKED, "MFA temporarily locked after repeated failures")
    if not code:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "MFA code required")
    valid = False
    if profile.totp_secret_ciphertext:
        valid = verify_totp(decrypt_totp_secret(settings, profile.totp_secret_ciphertext), code)
    if not valid and allow_recovery:
        digest = hash_recovery_code(settings, code)
        if digest in profile.recovery_code_hashes:
            profile.recovery_code_hashes = [item for item in profile.recovery_code_hashes if item != digest]
            valid = True
    if not valid:
        profile.failed_attempts += 1
        if profile.failed_attempts >= 5:
            profile.locked_until = now + timedelta(minutes=15)
            profile.failed_attempts = 0
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MFA code")
    profile.failed_attempts = 0
    profile.locked_until = None
    await db.flush()
    return True


async def step_up(
    db: AsyncSession,
    settings: Settings,
    user: User,
    auth_session_id: UUID,
    password: str,
    code: str | None,
    request: Request,
) -> AuthSession:
    if user.password_hash is None or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Password verification failed")
    profile = await get_profile(db, user.id)
    if profile.mfa_enabled:
        await verify_mfa(db, settings, user.id, code)
    item = await get_active_session(db, user.id, auth_session_id, lock=True)
    item.step_up_until = datetime.now(UTC) + timedelta(minutes=settings.STEP_UP_TTL_MINUTES)
    ip_address, user_agent = request_context(request)
    add_security_event(
        db,
        event_type="StepUpSucceeded",
        outcome="success",
        description="Sensitive-action step-up completed",
        user_id=user.id,
        actor_user_id=user.id,
        auth_session_id=item.id,
        severity="medium",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.flush()
    return item


async def list_security_events(
    db: AsyncSession, user_id: UUID, org_id: UUID | None, *, include_org: bool
) -> list[SecurityEvent]:
    filters = [SecurityEvent.user_id == user_id]
    if include_org and org_id is not None:
        filters.append(SecurityEvent.org_id == org_id)
    return list(
        (
            await db.scalars(
                select(SecurityEvent).where(or_(*filters)).order_by(SecurityEvent.occurred_at.desc()).limit(250)
            )
        ).all()
    )
