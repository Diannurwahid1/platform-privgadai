"""Auth endpoints: register / login / refresh / logout / me / verify-email."""

from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from uuid import UUID

from authx import TokenPayload
from fastapi import APIRouter, HTTPException, Request, Response, status

from dogeapi.auth import security_service
from dogeapi.auth.schemas import (
    LoginRequest,
    MessageResponse,
    MfaActivateRequest,
    MfaActivateResponse,
    MfaSetupResponse,
    PasswordConfirmation,
    RegisterRequest,
    RegisterResponse,
    SessionRevokeRequest,
    StepUpRequest,
    TokenPairResponse,
    UserResponse,
    VerifyEmailRequest,
)
from dogeapi.auth.service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate,
    mark_email_verified,
    register_user,
)
from dogeapi.auth.tokens import consume_email_verify_token, issue_email_verify_token
from dogeapi.deps import AuthDep, RedisDep, SessionDep, SettingsDep, TokenDep, UserDep

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair(
    auth: AuthDep, user_id: str, auth_session_id: UUID, *, mfa_authenticated: bool, fresh: bool = True
) -> TokenPairResponse:
    pair = auth.create_token_pair(
        uid=user_id,
        fresh=fresh,
        data={"sid": str(auth_session_id), "amr": ["pwd", "mfa"] if mfa_authenticated else ["pwd"]},
    )
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    body: RegisterRequest,
    response: Response,
    session: SessionDep,
    redis: RedisDep,
    auth: AuthDep,
    settings: SettingsDep,
) -> RegisterResponse:
    """Create a new user, issue tokens, and seed an email verification token.

    When ``FEATURE_EMAIL_DELIVERY`` is off the verification link is returned
    in the response body so a developer can complete signup without an SMTP
    server. When email delivery is on the link is sent by mail and not echoed.
    """
    try:
        user = await register_user(
            session,
            email=body.email,
            password=body.password,
            full_name=body.full_name,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from exc

    auth_session = await security_service.create_auth_session(
        session, settings, user.id, request, mfa_authenticated=False
    )
    tokens = _token_pair(auth, str(user.id), auth_session.id, mfa_authenticated=False)
    auth.set_access_cookies(tokens.access_token, response)
    auth.set_refresh_cookies(tokens.refresh_token, response)

    verify_token = await issue_email_verify_token(redis, user.id)
    verify_link = f"{settings.FRONTEND_BASE_URL}/verify-email?token={verify_token}"

    payload_link: str | None = None
    if not settings.FEATURE_EMAIL_DELIVERY:
        payload_link = verify_link
    else:
        from dogeapi.email import send_email_verification

        await send_email_verification(settings, to=user.email, link=verify_link)

    return RegisterResponse(
        user=UserResponse.model_validate(user),
        tokens=tokens,
        email_verification_link=payload_link,
    )


@router.post("/login", response_model=TokenPairResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    auth: AuthDep,
    settings: SettingsDep,
) -> TokenPairResponse:
    try:
        user = await authenticate(session, email=body.email, password=body.password)
    except InvalidCredentialsError as exc:
        ip_address, user_agent = security_service.request_context(request)
        security_service.add_security_event(
            session,
            event_type="LoginFailed",
            outcome="failure",
            description="Invalid email or password",
            severity="medium",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"email": str(body.email)},
        )
        await session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password") from exc

    profile = await security_service.get_profile(session, user.id)
    mfa_authenticated = False
    if profile.mfa_enabled:
        mfa_authenticated = await security_service.verify_mfa(session, settings, user.id, body.mfa_code)
    elif settings.PRIVILEGED_MFA_ENFORCED and await security_service.is_privileged_user(session, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Privileged account must enroll MFA before login")
    auth_session = await security_service.create_auth_session(
        session, settings, user.id, request, mfa_authenticated=mfa_authenticated
    )
    tokens = _token_pair(auth, str(user.id), auth_session.id, mfa_authenticated=mfa_authenticated)
    auth.set_access_cookies(tokens.access_token, response)
    auth.set_refresh_cookies(tokens.refresh_token, response)
    return tokens


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    request: Request,
    response: Response,
    auth: AuthDep,
    session: SessionDep,
    settings: SettingsDep,
) -> TokenPairResponse:
    """Exchange a refresh token for a fresh access+refresh pair."""
    payload: TokenPayload = await auth.refresh_token_required(request=request)
    user_id = str(payload.sub)
    extras = payload.model_extra or {}
    try:
        auth_session_id = UUID(str(extras.get("sid")))
        user_uuid = UUID(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token has no valid session") from exc
    auth_session = await security_service.get_active_session(session, user_uuid, auth_session_id, lock=True)
    auth_session.last_seen_at = datetime.now(UTC)
    auth_session.expires_at = datetime.now(UTC) + settings.jwt_refresh_expires
    data = {key: extras[key] for key in ("sid", "amr", "org_id", "role") if key in extras}
    pair = auth.create_token_pair(
        uid=user_id,
        fresh=False,
        data=data,
        access_scopes=list(payload.scopes or []),
        refresh_scopes=list(payload.scopes or []),
    )
    auth.set_access_cookies(pair.access_token, response)
    auth.set_refresh_cookies(pair.refresh_token, response)
    return TokenPairResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    auth: AuthDep,
    redis: RedisDep,
    payload: TokenDep,
    session: SessionDep,
    user: UserDep,
) -> MessageResponse:
    """Revoke the current access token via the token store and clear cookies.

    The blocklist key TTL matches the token's remaining lifetime, so we
    never accumulate stale entries.
    """
    auth.unset_cookies(response)

    raw_request_token = await auth.get_token_from_request(request, type="access", optional=True)
    if raw_request_token is not None:
        ttl = max(int(payload.time_until_expiry.total_seconds()), 1)
        await redis.setex(f"blocklist:{raw_request_token.token}", ttl, "1")

    sid = (payload.model_extra or {}).get("sid")
    if sid:
        with suppress(HTTPException):
            await security_service.revoke_session(session, user, UUID(str(sid)), "User logout")

    return MessageResponse(detail="Logged out")


@router.get("/me", response_model=UserResponse)
async def me(user: UserDep) -> UserResponse:
    return UserResponse.model_validate(user)


@router.get("/security")
async def security_overview(session: SessionDep, user: UserDep, payload: TokenDep) -> dict[str, object]:
    profile = await security_service.get_profile(session, user.id)
    sid = (payload.model_extra or {}).get("sid")
    return {
        "mfa_enabled": profile.mfa_enabled,
        "mfa_activated_at": profile.activated_at,
        "recovery_codes_remaining": len(profile.recovery_code_hashes),
        "current_session_id": sid,
    }


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def setup_mfa(
    body: PasswordConfirmation, request: Request, session: SessionDep, settings: SettingsDep, user: UserDep
) -> MfaSetupResponse:
    secret, uri = await security_service.begin_mfa_setup(session, settings, user, body.password, request)
    return MfaSetupResponse(secret=secret, otpauth_uri=uri)


@router.post("/mfa/activate", response_model=MfaActivateResponse)
async def activate_mfa(
    body: MfaActivateRequest, request: Request, session: SessionDep, settings: SettingsDep, user: UserDep
) -> MfaActivateResponse:
    codes = await security_service.activate_mfa(session, settings, user, body.code, request)
    return MfaActivateResponse(enabled=True, recovery_codes=codes)


@router.post("/step-up")
async def step_up_authentication(
    body: StepUpRequest,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    user: UserDep,
    payload: TokenDep,
) -> dict[str, object]:
    try:
        sid = UUID(str((payload.model_extra or {}).get("sid")))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has no valid session") from exc
    item = await security_service.step_up(session, settings, user, sid, body.password, body.mfa_code, request)
    return {"session_id": item.id, "step_up_until": item.step_up_until, "status": "verified"}


@router.get("/sessions")
async def auth_sessions(session: SessionDep, user: UserDep, payload: TokenDep) -> list[dict[str, object]]:
    current = str((payload.model_extra or {}).get("sid") or "")
    rows = await security_service.list_sessions(session, user.id)
    now = datetime.now(UTC)
    return [
        {
            "id": item.id,
            "ip_address": item.ip_address,
            "user_agent": item.user_agent,
            "created_at": item.created_at,
            "last_seen_at": item.last_seen_at,
            "expires_at": item.expires_at,
            "revoked_at": item.revoked_at,
            "revoke_reason": item.revoke_reason,
            "mfa_authenticated": item.mfa_authenticated,
            "step_up_until": item.step_up_until,
            "is_current": str(item.id) == current,
            "is_active": item.revoked_at is None and item.expires_at > now,
        }
        for item in rows
    ]


@router.post("/sessions/{auth_session_id}/revoke")
async def revoke_auth_session(
    auth_session_id: UUID,
    body: SessionRevokeRequest,
    session: SessionDep,
    user: UserDep,
    payload: TokenDep,
) -> dict[str, object]:
    try:
        current_id = UUID(str((payload.model_extra or {}).get("sid")))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has no valid session") from exc
    current = await security_service.get_active_session(session, user.id, current_id)
    if auth_session_id != current_id and (current.step_up_until is None or current.step_up_until <= datetime.now(UTC)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Step-up authentication required to revoke another session")
    item = await security_service.revoke_session(session, user, auth_session_id, body.reason)
    return {"id": item.id, "status": "revoked", "revoked_at": item.revoked_at}


@router.get("/security-events")
async def own_security_events(session: SessionDep, user: UserDep) -> list[dict[str, object]]:
    rows = await security_service.list_security_events(session, user.id, None, include_org=False)
    return [
        {
            "id": item.id,
            "event_type": item.event_type,
            "severity": item.severity,
            "outcome": item.outcome,
            "description": item.description,
            "ip_address": item.ip_address,
            "user_agent": item.user_agent,
            "event_metadata": item.event_metadata,
            "occurred_at": item.occurred_at,
        }
        for item in rows
    ]


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: VerifyEmailRequest,
    session: SessionDep,
    redis: RedisDep,
) -> MessageResponse:
    user_id = await consume_email_verify_token(redis, body.token)
    if user_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid or expired verification token",
        )
    await mark_email_verified(session, user_id)
    return MessageResponse(detail="Email verified")
