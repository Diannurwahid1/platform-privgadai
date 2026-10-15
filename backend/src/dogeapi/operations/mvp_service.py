"""Transactional services for the PrivGadai MVP workflow."""

from __future__ import annotations

import asyncio
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    ApplicationStatusHistory,
    Asset,
    AssetCategory,
    Borrower,
    Branch,
    CashTransaction,
    CollateralEvent,
    CollectionCase,
    Consent,
    CustodyEvent,
    CustodyLocation,
    CustodyMovement,
    CustomerAcceptance,
    DebtorProfile,
    EvidenceFile,
    HumanAppraisal,
    Incident,
    KycVerification,
    LoanAccount,
    LoanApplication,
    LoanProduct,
    Membership,
    Offer,
    PawnAgreement,
    PickupTask,
    SettlementVerification,
    StaffAssignment,
    User,
)
from dogeapi.operations.mvp_schemas import (
    ApplicationCreate,
    ApplicationDetail,
    AppraisalCreate,
    AssetCategoryCreate,
    BranchCreate,
    CollateralTimeline,
    CustodyEventCreate,
    CustodyLocationCreate,
    CustodyMovementCreate,
    EvidenceCreate,
    IncidentCreate,
    LoanProductCreate,
    OfferCreate,
    PickupCreate,
    SettlementCreate,
    StaffAssignmentCreate,
)
from dogeapi.operations.state_machine import (
    APPLICATION_TRANSITIONS,
    COLLATERAL_TRANSITIONS,
    LOAN_TRANSITIONS,
    can_transition,
)


def _not_found(label: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{label} not found")


def _conflict(message: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, message)


def _mask_phone(phone: str) -> str:
    clean = "".join(character for character in phone if character.isdigit() or character == "+")
    if len(clean) <= 6:
        return clean[:2] + "***"
    return f"{clean[:4]}****{clean[-3:]}"


async def list_branches(session: AsyncSession, org_id: UUID) -> list[Branch]:
    return list(await session.scalars(select(Branch).where(Branch.org_id == org_id).order_by(Branch.code)))


async def create_branch(session: AsyncSession, org_id: UUID, data: BranchCreate) -> Branch:
    item = Branch(org_id=org_id, **data.model_dump())
    session.add(item)
    await _flush_or_conflict(session, "Branch code already exists")
    from dogeapi.operations import erp_service

    await erp_service.ensure_finance_masters(session, org_id, item.id)
    return item


async def list_asset_categories(session: AsyncSession, org_id: UUID) -> list[AssetCategory]:
    return list(
        await session.scalars(select(AssetCategory).where(AssetCategory.org_id == org_id).order_by(AssetCategory.code))
    )


async def create_asset_category(session: AsyncSession, org_id: UUID, data: AssetCategoryCreate) -> AssetCategory:
    item = AssetCategory(org_id=org_id, **data.model_dump())
    session.add(item)
    await _flush_or_conflict(session, "Asset category code already exists")
    return item


async def list_loan_products(session: AsyncSession, org_id: UUID) -> list[LoanProduct]:
    return list(
        await session.scalars(select(LoanProduct).where(LoanProduct.org_id == org_id).order_by(LoanProduct.code))
    )


async def create_loan_product(session: AsyncSession, org_id: UUID, data: LoanProductCreate) -> LoanProduct:
    item = LoanProduct(org_id=org_id, **data.model_dump())
    session.add(item)
    await _flush_or_conflict(session, "Loan product code already exists")
    return item


async def create_custody_location(session: AsyncSession, org_id: UUID, data: CustodyLocationCreate) -> CustodyLocation:
    branch = await session.scalar(select(Branch).where(Branch.id == data.branch_id, Branch.org_id == org_id))
    if branch is None:
        raise _not_found("Branch")
    item = CustodyLocation(org_id=org_id, **data.model_dump())
    session.add(item)
    await _flush_or_conflict(session, "Custody location code already exists")
    return item


async def list_custody_locations(session: AsyncSession, org_id: UUID) -> list[CustodyLocation]:
    return list(
        await session.scalars(
            select(CustodyLocation).where(CustodyLocation.org_id == org_id).order_by(CustodyLocation.code)
        )
    )


async def list_staff_assignments(session: AsyncSession, org_id: UUID) -> list[dict[str, object]]:
    rows = (
        await session.execute(
            select(StaffAssignment, User.full_name, Branch.name)
            .join(User, User.id == StaffAssignment.user_id)
            .join(Branch, Branch.id == StaffAssignment.branch_id)
            .where(StaffAssignment.org_id == org_id, Branch.org_id == org_id)
            .order_by(Branch.code, User.full_name)
        )
    ).all()
    return [
        {
            "id": assignment.id,
            "user_id": assignment.user_id,
            "user_name": user_name,
            "branch_id": assignment.branch_id,
            "branch_name": branch_name,
            "operational_role": assignment.operational_role,
            "is_active": assignment.is_active,
        }
        for assignment, user_name, branch_name in rows
    ]


async def create_staff_assignment(
    session: AsyncSession, org_id: UUID, data: StaffAssignmentCreate
) -> dict[str, object]:
    membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == data.user_id)
    )
    branch = await session.scalar(select(Branch).where(Branch.org_id == org_id, Branch.id == data.branch_id))
    if membership is None:
        raise _not_found("Organization member")
    if branch is None:
        raise _not_found("Branch")
    user = await session.get(User, data.user_id)
    item = StaffAssignment(org_id=org_id, **data.model_dump())
    session.add(item)
    await _flush_or_conflict(session, "Staff assignment already exists")
    return {
        "id": item.id,
        "user_id": item.user_id,
        "user_name": user.full_name if user else "Unknown",
        "branch_id": item.branch_id,
        "branch_name": branch.name,
        "operational_role": item.operational_role,
        "is_active": item.is_active,
    }


async def create_application(
    session: AsyncSession, org_id: UUID, actor_id: UUID | None, data: ApplicationCreate
) -> LoanApplication:
    branch = await session.scalar(select(Branch).where(Branch.id == data.branch_id, Branch.org_id == org_id))
    product = await session.scalar(
        select(LoanProduct).where(
            LoanProduct.id == data.product_id, LoanProduct.org_id == org_id, LoanProduct.is_active
        )
    )
    category = await session.scalar(
        select(AssetCategory).where(
            AssetCategory.org_id == org_id,
            AssetCategory.code == data.asset.category_code,
            AssetCategory.is_active,
        )
    )
    if branch is None or not branch.is_active:
        raise _not_found("Active branch")
    if product is None:
        raise _not_found("Active loan product")
    if category is None:
        raise _not_found("Active asset category")
    if actor_id is not None:
        await ensure_operational_access(
            session, org_id, actor_id, branch.id, {"ops_admin", "branch_manager", "loan_officer"}
        )
    if not product.min_amount <= data.requested_amount <= product.max_amount:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Requested amount is outside product limits")
    if data.requested_tenor_days not in product.allowed_tenors_days:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Tenor is not allowed by this product")

    stamp = datetime.now(UTC).strftime("%y%m%d")
    suffix = secrets.token_hex(3).upper()
    borrower = Borrower(
        org_id=org_id,
        customer_reference=data.borrower.customer_reference or f"CUS-{stamp}-{suffix}",
        full_name=data.borrower.full_name,
        phone_masked=_mask_phone(data.borrower.phone),
    )
    session.add(borrower)
    await session.flush()
    session.add(DebtorProfile(org_id=org_id, borrower_id=borrower.id))

    initial_status = "submitted" if data.submit else "draft"
    now = datetime.now(UTC)
    application = LoanApplication(
        org_id=org_id,
        branch_id=branch.id,
        borrower_id=borrower.id,
        assigned_user_id=actor_id,
        product_id=product.id,
        application_no=f"PG-{stamp}-{suffix}",
        status=initial_status,
        priority=data.priority,
        asset_category=category.code,
        requested_amount=data.requested_amount,
        requested_tenor_days=data.requested_tenor_days,
        purpose=data.purpose,
        submitted_at=now if data.submit else None,
        sla_due_at=now + timedelta(hours=24) if data.submit else None,
    )
    session.add(application)
    await session.flush()

    asset = Asset(
        org_id=org_id,
        application_id=application.id,
        asset_code=f"AST-{stamp}-{suffix}",
        category=category.code,
        brand=data.asset.brand,
        model=data.asset.model,
        condition_grade=data.asset.condition_grade,
        indicative_value=data.asset.indicative_value,
    )
    session.add_all(
        [
            asset,
            Consent(
                org_id=org_id,
                borrower_id=borrower.id,
                consent_type="privacy_and_credit_processing",
                document_version=data.consent_document_version,
                channel="web",
            ),
            ApplicationStatusHistory(
                org_id=org_id,
                application_id=application.id,
                actor_user_id=actor_id,
                from_status=None,
                to_status=initial_status,
                note="Application created",
            ),
            CollateralEvent(
                org_id=org_id,
                application_id=application.id,
                actor_user_id=actor_id,
                event_type="registered",
                title="Collateral registered",
                description="Asset identity created with customer custody",
                event_metadata={"asset_code": asset.asset_code, "category": category.code},
            ),
        ]
    )
    await session.flush()
    return application


async def list_field_tasks(session: AsyncSession, org_id: UUID, user_id: UUID) -> list[dict[str, object]]:
    membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id)
    )
    if membership is None:
        raise _not_found("Membership")
    statement = (
        select(PickupTask, LoanApplication, Borrower, Asset, Branch)
        .join(LoanApplication, LoanApplication.id == PickupTask.application_id)
        .join(Borrower, Borrower.id == LoanApplication.borrower_id)
        .join(Asset, Asset.application_id == LoanApplication.id)
        .join(Branch, Branch.id == LoanApplication.branch_id)
        .where(
            PickupTask.org_id == org_id,
            LoanApplication.org_id == org_id,
            Borrower.org_id == org_id,
            Asset.org_id == org_id,
            Branch.org_id == org_id,
        )
        .order_by(PickupTask.scheduled_at.asc().nullslast(), PickupTask.created_at.desc())
    )
    if membership.role.value == "member":
        assignment = await session.scalar(
            select(StaffAssignment).where(
                StaffAssignment.org_id == org_id,
                StaffAssignment.user_id == user_id,
                StaffAssignment.operational_role == "field_agent",
                StaffAssignment.is_active,
            )
        )
        if assignment is None:
            return []
        statement = statement.where(PickupTask.assigned_user_id == user_id)
    rows = (await session.execute(statement)).all()
    return [
        {
            "id": pickup.id,
            "application_id": application.id,
            "application_no": application.application_no,
            "assignment_code": pickup.assignment_code,
            "status": pickup.status,
            "scheduled_at": pickup.scheduled_at,
            "pickup_address": pickup.pickup_address,
            "borrower_name": borrower.full_name,
            "phone_masked": borrower.phone_masked,
            "asset_label": " ".join(value for value in (asset.brand, asset.model) if value) or asset.category,
            "branch_name": branch.name,
        }
        for pickup, application, borrower, asset, branch in rows
    ]


async def ensure_operational_access(
    session: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    branch_id: UUID,
    allowed_roles: set[str],
) -> None:
    membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id)
    )
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No membership in active tenant")
    if membership.role.value in {"owner", "admin"}:
        return
    assignment = await session.scalar(
        select(StaffAssignment).where(
            StaffAssignment.org_id == org_id,
            StaffAssignment.user_id == user_id,
            StaffAssignment.branch_id == branch_id,
            StaffAssignment.operational_role.in_(allowed_roles),
            StaffAssignment.is_active,
        )
    )
    if assignment is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Operational role or branch assignment is insufficient")


async def ensure_any_operational_role(
    session: AsyncSession, org_id: UUID, user_id: UUID, allowed_roles: set[str]
) -> None:
    membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id)
    )
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No membership in active tenant")
    if membership.role.value in {"owner", "admin"}:
        return
    assignment = await session.scalar(
        select(StaffAssignment).where(
            StaffAssignment.org_id == org_id,
            StaffAssignment.user_id == user_id,
            StaffAssignment.operational_role.in_(allowed_roles),
            StaffAssignment.is_active,
        )
    )
    if assignment is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Operational role is insufficient")


async def get_application(session: AsyncSession, org_id: UUID, application_id: UUID) -> LoanApplication:
    application = await session.scalar(
        select(LoanApplication).where(LoanApplication.id == application_id, LoanApplication.org_id == org_id)
    )
    if application is None:
        raise _not_found("Application")
    return application


async def transition_application(
    session: AsyncSession, org_id: UUID, actor_id: UUID, application_id: UUID, target: str, note: str | None
) -> LoanApplication:
    application = await get_application(session, org_id, application_id)
    await ensure_operational_access(
        session, org_id, actor_id, application.branch_id, {"ops_admin", "branch_manager", "loan_officer", "reviewer"}
    )
    if not can_transition(APPLICATION_TRANSITIONS, application.status, target):
        raise _conflict(f"Cannot transition application from {application.status} to {target}")
    if target == "appraisal":
        verified_kyc = await session.scalar(
            select(KycVerification.id)
            .where(
                KycVerification.org_id == org_id,
                KycVerification.borrower_id == application.borrower_id,
                KycVerification.status == "verified",
                (KycVerification.expires_at.is_(None) | (KycVerification.expires_at > datetime.now(UTC))),
            )
            .limit(1)
        )
        if verified_kyc is None:
            raise _conflict("KYC debitur harus terverifikasi dan masih berlaku sebelum penaksiran")
    previous = application.status
    application.status = target
    application.revision += 1
    if target == "submitted" and application.submitted_at is None:
        application.submitted_at = datetime.now(UTC)
        application.sla_due_at = datetime.now(UTC) + timedelta(hours=24)
    session.add(
        ApplicationStatusHistory(
            org_id=org_id,
            application_id=application.id,
            actor_user_id=actor_id,
            from_status=previous,
            to_status=target,
            note=note,
        )
    )
    await session.flush()
    return application


async def add_evidence(
    session: AsyncSession, org_id: UUID, actor_id: UUID, application_id: UUID, data: EvidenceCreate
) -> EvidenceFile:
    application = await get_application(session, org_id, application_id)
    await ensure_operational_access(
        session,
        org_id,
        actor_id,
        application.branch_id,
        {"ops_admin", "branch_manager", "loan_officer", "reviewer", "appraiser", "field_agent"},
    )
    item = EvidenceFile(org_id=org_id, application_id=application_id, scan_status="pending", **data.model_dump())
    session.add(item)
    await session.flush()
    return item


async def store_evidence_upload(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    application_id: UUID,
    evidence_type: str,
    file_name: str,
    content_type: str,
    content: bytes,
) -> EvidenceFile:
    application = await get_application(session, org_id, application_id)
    await ensure_operational_access(
        session,
        org_id,
        actor_id,
        application.branch_id,
        {"ops_admin", "branch_manager", "loan_officer", "reviewer", "appraiser", "field_agent"},
    )
    digest = hashlib.sha256(content).hexdigest()
    safe_suffix = Path(file_name).suffix.lower()[:10]
    relative_key = f"{org_id}/{application_id}/{secrets.token_hex(16)}{safe_suffix}"
    storage_root = Path(__file__).resolve().parents[3] / ".data" / "evidence"
    target = (storage_root / relative_key).resolve()
    if storage_root.resolve() not in target.parents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid evidence path")
    target.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(target.write_bytes, content)
    item = EvidenceFile(
        org_id=org_id,
        application_id=application_id,
        evidence_type=evidence_type,
        file_name=Path(file_name).name,
        object_key=relative_key,
        content_type=content_type,
        size_bytes=len(content),
        sha256=digest,
        scan_status="pending",
    )
    session.add(item)
    await session.flush()
    return item


async def create_appraisal(
    session: AsyncSession, org_id: UUID, actor_id: UUID, data: AppraisalCreate
) -> HumanAppraisal:
    application = await get_application(session, org_id, data.application_id)
    await ensure_operational_access(
        session, org_id, actor_id, application.branch_id, {"ops_admin", "branch_manager", "appraiser"}
    )
    if application.status != "appraisal":
        raise _conflict("Application must be in appraisal status")
    if data.liquidation_value > data.market_value or data.recommended_loan > data.liquidation_value:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Recommended loan must not exceed liquidation value and liquidation value must not exceed market value",
        )
    revision = (
        int(
            (
                await session.scalar(
                    select(func.coalesce(func.max(HumanAppraisal.revision), 0)).where(
                        HumanAppraisal.org_id == org_id, HumanAppraisal.application_id == application.id
                    )
                )
            )
            or 0
        )
        + 1
    )
    item = HumanAppraisal(
        org_id=org_id,
        appraiser_user_id=actor_id,
        revision=revision,
        status="pending_approval",
        **data.model_dump(),
    )
    session.add(item)
    await session.flush()
    from dogeapi.operations import approval_service

    await approval_service.request_approval(
        session,
        org_id=org_id,
        branch_id=application.branch_id,
        aggregate_type="appraisal",
        aggregate_id=item.id,
        aggregate_reference=application.application_no,
        action="approve_appraisal",
        requested_by=actor_id,
        assigned_role="branch_manager",
        reason=f"Appraisal revision {revision} menunggu review supervisor",
        payload={
            "application_id": str(application.id),
            "revision": revision,
            "market_value": str(item.market_value),
            "liquidation_value": str(item.liquidation_value),
            "recommended_loan": str(item.recommended_loan),
            "condition_grade": item.condition_grade,
            "rationale": item.rationale,
        },
        priority=application.priority,
    )
    return item


async def create_offer(session: AsyncSession, org_id: UUID, actor_id: UUID, data: OfferCreate) -> Offer:
    application = await get_application(session, org_id, data.application_id)
    await ensure_operational_access(
        session, org_id, actor_id, application.branch_id, {"ops_admin", "branch_manager", "reviewer"}
    )
    if application.status != "appraisal":
        raise _conflict("Application must be in appraisal status")
    appraisal = await session.scalar(
        select(HumanAppraisal)
        .where(
            HumanAppraisal.org_id == org_id,
            HumanAppraisal.application_id == application.id,
            HumanAppraisal.status == "final",
        )
        .order_by(HumanAppraisal.revision.desc())
    )
    product = await session.scalar(
        select(LoanProduct).where(LoanProduct.org_id == org_id, LoanProduct.id == application.product_id)
    )
    if appraisal is None or product is None:
        raise _conflict("A final human appraisal and loan product are required")
    max_by_ltv = appraisal.liquidation_value * product.max_ltv_percent / Decimal("100")
    if data.principal_amount > min(appraisal.recommended_loan, max_by_ltv):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Offer exceeds appraisal or product LTV limit")
    if data.tenor_days not in product.allowed_tenors_days:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Offer tenor is not allowed by product")
    if data.expires_at <= datetime.now(UTC):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Offer expiry must be in the future")
    version = (
        int(
            (
                await session.scalar(
                    select(func.coalesce(func.max(Offer.version), 0)).where(
                        Offer.org_id == org_id, Offer.application_id == application.id
                    )
                )
            )
            or 0
        )
        + 1
    )
    item = Offer(
        org_id=org_id,
        created_by_user_id=actor_id,
        version=version,
        total_due_amount=data.principal_amount + data.service_fee_amount,
        **data.model_dump(),
    )
    session.add(item)
    await session.flush()
    await transition_application(session, org_id, actor_id, application.id, "offered", "Human-approved offer issued")
    return item


async def accept_offer(
    session: AsyncSession, org_id: UUID, actor_id: UUID, offer_id: UUID, channel: str, ip_address: str | None
) -> LoanAccount:
    row = (
        await session.execute(
            select(Offer, LoanApplication)
            .join(LoanApplication, LoanApplication.id == Offer.application_id)
            .where(Offer.id == offer_id, Offer.org_id == org_id, LoanApplication.org_id == org_id)
        )
    ).one_or_none()
    if row is None:
        raise _not_found("Offer")
    offer, application = row
    await ensure_operational_access(
        session, org_id, actor_id, application.branch_id, {"ops_admin", "branch_manager", "loan_officer", "reviewer"}
    )
    if offer.status != "offered" or application.status != "offered":
        raise _conflict("Offer is no longer available")
    if offer.expires_at <= datetime.now(UTC):
        offer.status = "expired"
        raise _conflict("Offer has expired")
    offer.status = "accepted"
    session.add(
        CustomerAcceptance(
            org_id=org_id,
            offer_id=offer.id,
            borrower_id=application.borrower_id,
            channel=channel,
            ip_address=ip_address,
        )
    )
    account = LoanAccount(
        org_id=org_id,
        application_id=application.id,
        account_no=f"LN-{datetime.now(UTC).strftime('%y%m%d')}-{secrets.token_hex(3).upper()}",
        principal_amount=offer.principal_amount,
        total_due_amount=offer.total_due_amount,
        outstanding_principal=Decimal("0"),
        outstanding_fee=Decimal("0"),
        paid_amount=Decimal("0"),
    )
    product = await session.scalar(
        select(LoanProduct).where(LoanProduct.org_id == org_id, LoanProduct.id == application.product_id)
    )
    agreement = PawnAgreement(
        org_id=org_id,
        application_id=application.id,
        offer_id=offer.id,
        sbg_number=f"SBG-{datetime.now(UTC).strftime('%y%m%d')}-{secrets.token_hex(3).upper()}",
        agreement_type=product.agreement_type if product else "pawn",
        document_version=offer.agreement_version,
    )
    session.add_all([account, agreement])
    await transition_application(session, org_id, actor_id, application.id, "accepted", "Offer accepted by customer")
    session.add(
        CollateralEvent(
            org_id=org_id,
            application_id=application.id,
            actor_user_id=actor_id,
            event_type="offer_accepted",
            title="Offer accepted",
            description=f"Agreement {offer.agreement_version} accepted through {channel}",
            event_metadata={"offer_id": str(offer.id)},
        )
    )
    await session.flush()
    return account


async def create_pickup(session: AsyncSession, org_id: UUID, actor_id: UUID, data: PickupCreate) -> PickupTask:
    application = await get_application(session, org_id, data.application_id)
    await ensure_operational_access(
        session, org_id, actor_id, application.branch_id, {"ops_admin", "branch_manager", "loan_officer"}
    )
    if application.status != "accepted":
        raise _conflict("Application must have an accepted offer")
    existing = await session.scalar(
        select(PickupTask).where(PickupTask.org_id == org_id, PickupTask.application_id == application.id)
    )
    if existing is not None:
        raise _conflict("Pickup task already exists")
    asset = await _get_asset(session, org_id, application.id)
    _set_collateral_status(asset, "pickup_assigned")
    item = PickupTask(
        org_id=org_id,
        assignment_code=f"PU-{secrets.token_hex(4).upper()}",
        status="assigned",
        **data.model_dump(),
    )
    session.add(item)
    _add_collateral_event(session, org_id, application.id, actor_id, "pickup_assigned", "Pickup assigned")
    await session.flush()
    return item


async def transition_pickup(
    session: AsyncSession, org_id: UUID, actor_id: UUID, pickup_id: UUID, target: str, note: str | None
) -> PickupTask:
    item = await session.scalar(select(PickupTask).where(PickupTask.id == pickup_id, PickupTask.org_id == org_id))
    if item is None:
        raise _not_found("Pickup task")
    application = await get_application(session, org_id, item.application_id)
    await ensure_operational_access(
        session, org_id, actor_id, application.branch_id, {"ops_admin", "branch_manager", "field_agent"}
    )
    asset = await _get_asset(session, org_id, item.application_id)
    collateral_target = target
    _set_collateral_status(asset, collateral_target)
    item.status = target
    item.condition_note = note
    _add_collateral_event(
        session, org_id, item.application_id, actor_id, target, target.replace("_", " ").title(), note
    )
    await session.flush()
    return item


async def create_custody_event(
    session: AsyncSession, org_id: UUID, actor_id: UUID, data: CustodyEventCreate
) -> CustodyEvent:
    application = await get_application(session, org_id, data.application_id)
    await ensure_operational_access(
        session, org_id, actor_id, application.branch_id, {"ops_admin", "branch_manager", "custodian"}
    )
    location = await session.scalar(
        select(CustodyLocation).where(CustodyLocation.id == data.location_id, CustodyLocation.org_id == org_id)
    )
    if location is None:
        raise _not_found("Custody location")
    if data.event_type == "release_authorized":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Otorisasi pelepasan agunan hanya dapat diterbitkan melalui approval inbox",
        )
    asset = await _get_asset(session, org_id, data.application_id)
    _set_collateral_status(asset, data.event_type)
    item = CustodyEvent(org_id=org_id, actor_user_id=actor_id, **data.model_dump())
    session.add(item)
    _add_collateral_event(
        session,
        org_id,
        data.application_id,
        actor_id,
        data.event_type,
        data.event_type.replace("_", " ").title(),
        data.condition_note,
        {"location_id": str(location.id), "location": location.name},
    )
    await session.flush()
    return item


async def list_custody_movements(session: AsyncSession, org_id: UUID) -> list[dict[str, object]]:
    rows = list(
        await session.scalars(
            select(CustodyMovement)
            .where(CustodyMovement.org_id == org_id)
            .order_by(CustodyMovement.created_at.desc())
            .limit(200)
        )
    )
    return [
        {
            "id": item.id,
            "movement_no": item.movement_no,
            "application_id": item.application_id,
            "from_location_id": item.from_location_id,
            "to_location_id": item.to_location_id,
            "status": item.status,
            "reason": item.reason,
            "seal_out": item.seal_out,
            "seal_in": item.seal_in,
            "requested_by_user_id": item.requested_by_user_id,
            "dispatched_by_user_id": item.dispatched_by_user_id,
            "received_by_user_id": item.received_by_user_id,
            "created_at": item.created_at,
            "dispatched_at": item.dispatched_at,
            "received_at": item.received_at,
        }
        for item in rows
    ]


async def request_custody_movement(
    session: AsyncSession, org_id: UUID, actor_id: UUID, data: CustodyMovementCreate
) -> CustodyMovement:
    application = await get_application(session, org_id, data.application_id)
    await ensure_operational_access(
        session, org_id, actor_id, application.branch_id, {"ops_admin", "branch_manager", "custodian"}
    )
    asset = await _get_asset(session, org_id, application.id)
    if asset.collateral_status != "stored":
        raise _conflict("Only stored collateral can be moved")
    latest = await session.scalar(
        select(CustodyEvent)
        .where(CustodyEvent.org_id == org_id, CustodyEvent.application_id == application.id)
        .order_by(CustodyEvent.occurred_at.desc())
        .limit(1)
    )
    destination = await session.scalar(
        select(CustodyLocation).where(
            CustodyLocation.org_id == org_id, CustodyLocation.id == data.to_location_id, CustodyLocation.is_active
        )
    )
    if latest is None or destination is None:
        raise _not_found("Active custody location")
    if latest.location_id == destination.id:
        raise _conflict("Destination must differ from current custody location")
    active = await session.scalar(
        select(CustodyMovement).where(
            CustodyMovement.org_id == org_id,
            CustodyMovement.application_id == application.id,
            CustodyMovement.status.in_({"requested", "in_transit"}),
        )
    )
    if active is not None:
        raise _conflict("Collateral already has an active movement")
    item = CustodyMovement(
        org_id=org_id,
        application_id=application.id,
        movement_no=f"MOV-{datetime.now(UTC):%y%m%d}-{secrets.token_hex(3).upper()}",
        from_location_id=latest.location_id,
        to_location_id=destination.id,
        requested_by_user_id=actor_id,
        reason=data.reason,
    )
    session.add(item)
    _add_collateral_event(
        session,
        org_id,
        application.id,
        actor_id,
        "movement_requested",
        "Custody movement requested",
        data.reason,
        {
            "movement_id": str(item.id),
            "from_location_id": str(latest.location_id),
            "to_location_id": str(destination.id),
        },
    )
    await session.flush()
    return item


async def dispatch_custody_movement(
    session: AsyncSession, org_id: UUID, actor_id: UUID, movement_id: UUID, seal: str, note: str
) -> CustodyMovement:
    item = await session.scalar(
        select(CustodyMovement)
        .where(CustodyMovement.org_id == org_id, CustodyMovement.id == movement_id)
        .with_for_update()
    )
    if item is None:
        raise _not_found("Custody movement")
    if item.status != "requested":
        raise _conflict("Movement is not ready for dispatch")
    location = await session.scalar(
        select(CustodyLocation).where(CustodyLocation.org_id == org_id, CustodyLocation.id == item.from_location_id)
    )
    await ensure_operational_access(
        session, org_id, actor_id, location.branch_id, {"ops_admin", "branch_manager", "custodian"}
    )
    item.status = "in_transit"
    item.seal_out = seal
    item.dispatch_note = note
    item.dispatched_by_user_id = actor_id
    item.dispatched_at = datetime.now(UTC)
    _add_collateral_event(
        session,
        org_id,
        item.application_id,
        actor_id,
        "custody_dispatched",
        "Custody transfer dispatched",
        note,
        {"movement_id": str(item.id), "seal": seal},
    )
    await session.flush()
    return item


async def receive_custody_movement(
    session: AsyncSession, org_id: UUID, actor_id: UUID, movement_id: UUID, seal: str, note: str
) -> CustodyMovement:
    item = await session.scalar(
        select(CustodyMovement)
        .where(CustodyMovement.org_id == org_id, CustodyMovement.id == movement_id)
        .with_for_update()
    )
    if item is None:
        raise _not_found("Custody movement")
    if item.status != "in_transit":
        raise _conflict("Movement is not in transit")
    if actor_id in {item.requested_by_user_id, item.dispatched_by_user_id}:
        raise _conflict("Receiver must be different from requester and dispatcher")
    if seal != item.seal_out:
        raise HTTPException(status.HTTP_409_CONFLICT, "Inbound seal does not match outbound seal")
    location = await session.scalar(
        select(CustodyLocation).where(CustodyLocation.org_id == org_id, CustodyLocation.id == item.to_location_id)
    )
    await ensure_operational_access(
        session, org_id, actor_id, location.branch_id, {"ops_admin", "branch_manager", "custodian"}
    )
    item.status = "received"
    item.seal_in = seal
    item.receipt_note = note
    item.received_by_user_id = actor_id
    item.received_at = datetime.now(UTC)
    session.add(
        CustodyEvent(
            org_id=org_id,
            application_id=item.application_id,
            location_id=item.to_location_id,
            actor_user_id=actor_id,
            event_type="stored",
            condition_note=note,
        )
    )
    _add_collateral_event(
        session,
        org_id,
        item.application_id,
        actor_id,
        "custody_moved",
        "Custody transfer received",
        note,
        {"movement_id": str(item.id), "seal": seal, "location_id": str(item.to_location_id)},
    )
    await session.flush()
    return item


async def disburse_loan(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    application_id: UUID,
    external_reference: str,
    idempotency_key: str,
) -> LoanAccount:
    application = await get_application(session, org_id, application_id)
    await ensure_operational_access(
        session, org_id, actor_id, application.branch_id, {"ops_admin", "branch_manager", "finance"}
    )
    account = await session.scalar(
        select(LoanAccount).where(LoanAccount.org_id == org_id, LoanAccount.application_id == application_id)
    )
    if account is None:
        raise _not_found("Loan account")
    existing = await session.scalar(
        select(CashTransaction).where(
            CashTransaction.org_id == org_id, CashTransaction.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return account
    if not can_transition(LOAN_TRANSITIONS, account.status, "active"):
        raise _conflict(f"Cannot disburse loan in {account.status} status")
    offer = await session.scalar(
        select(Offer).where(Offer.org_id == org_id, Offer.application_id == application_id, Offer.status == "accepted")
    )
    account.status = "active"
    account.disbursement_reference = external_reference
    account.disbursed_at = datetime.now(UTC)
    account.due_at = account.disbursed_at + timedelta(days=offer.tenor_days if offer else 30)
    from dogeapi.operations import erp_service

    await erp_service.post_disbursement(
        session, org_id, actor_id, application, account, external_reference, idempotency_key
    )
    session.add(
        CollectionCase(
            org_id=org_id,
            loan_account_id=account.id,
            due_at=account.due_at,
            outstanding_amount=account.total_due_amount,
            aging_bucket="current",
            status="monitoring",
        )
    )
    _add_collateral_event(
        session,
        org_id,
        application_id,
        actor_id,
        "loan_disbursed",
        "Loan disbursed",
        event_metadata={"reference": external_reference},
    )
    await session.flush()
    return account


async def verify_settlement(
    session: AsyncSession, org_id: UUID, actor_id: UUID, data: SettlementCreate
) -> SettlementVerification:
    application = await get_application(session, org_id, data.application_id)
    await ensure_operational_access(
        session, org_id, actor_id, application.branch_id, {"ops_admin", "branch_manager", "finance"}
    )
    account = await session.scalar(
        select(LoanAccount).where(LoanAccount.org_id == org_id, LoanAccount.application_id == data.application_id)
    )
    if account is None:
        raise _not_found("Loan account")
    existing = await session.scalar(
        select(CashTransaction).where(
            CashTransaction.org_id == org_id, CashTransaction.idempotency_key == data.idempotency_key
        )
    )
    if existing is not None:
        existing_verification = await session.scalar(
            select(SettlementVerification).where(
                SettlementVerification.org_id == org_id,
                SettlementVerification.application_id == data.application_id,
                SettlementVerification.external_reference == data.external_reference,
            )
        )
        if existing_verification is None:
            raise _conflict("Idempotency key was used for another transaction")
        return existing_verification
    if not can_transition(LOAN_TRANSITIONS, account.status, "settled"):
        raise _conflict(f"Cannot settle loan in {account.status} status")
    if data.settlement_type == "repayment" and data.amount != account.total_due_amount:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Repayment amount must equal total due")
    item = SettlementVerification(
        org_id=org_id,
        verified_by_user_id=actor_id,
        **data.model_dump(exclude={"idempotency_key"}),
    )
    session.add(item)
    from dogeapi.operations import erp_service

    await erp_service.post_repayment(
        session,
        org_id,
        actor_id,
        application,
        account,
        data.amount,
        data.external_reference,
        data.idempotency_key,
    )
    account.status = "settled"
    account.settled_at = datetime.now(UTC)
    asset = await _get_asset(session, org_id, data.application_id)
    _add_collateral_event(
        session,
        org_id,
        data.application_id,
        actor_id,
        "settled",
        "Settlement verified",
        event_metadata={"type": data.settlement_type, "reference": data.external_reference},
    )
    if asset.collateral_status == "stored":
        latest_custody = await session.scalar(
            select(CustodyEvent)
            .where(
                CustodyEvent.org_id == org_id,
                CustodyEvent.application_id == data.application_id,
            )
            .order_by(CustodyEvent.occurred_at.desc())
            .limit(1)
        )
        if latest_custody is None:
            raise _conflict("Lokasi custody aktif tidak ditemukan untuk proses pelepasan")
        from dogeapi.operations import approval_service

        await approval_service.request_approval(
            session,
            org_id=org_id,
            branch_id=application.branch_id,
            aggregate_type="custody_release",
            aggregate_id=application.id,
            aggregate_reference=application.application_no,
            action="authorize_collateral_release",
            requested_by=actor_id,
            assigned_role="branch_manager",
            reason="Pelunasan terverifikasi; agunan menunggu otorisasi pelepasan",
            payload={
                "application_id": str(application.id),
                "loan_account_id": str(account.id),
                "settlement_id": str(item.id),
                "location_id": str(latest_custody.location_id),
                "condition_note": "Release approved after verified settlement",
                "settlement_reference": data.external_reference,
                "settlement_amount": str(data.amount),
            },
            priority="high",
            sla_hours=4,
        )
        _add_collateral_event(
            session,
            org_id,
            data.application_id,
            actor_id,
            "release_requested",
            "Release approval requested",
            "Pelunasan terverifikasi dan menunggu checker independen.",
            {"settlement_reference": data.external_reference},
        )
    await session.flush()
    return item


async def create_incident(session: AsyncSession, org_id: UUID, actor_id: UUID, data: IncidentCreate) -> Incident:
    application = await get_application(session, org_id, data.application_id)
    await ensure_operational_access(
        session,
        org_id,
        actor_id,
        application.branch_id,
        {"ops_admin", "branch_manager", "loan_officer", "reviewer", "appraiser", "field_agent", "custodian", "finance"},
    )
    asset = await _get_asset(session, org_id, data.application_id)
    if can_transition(COLLATERAL_TRANSITIONS, asset.collateral_status, "incident_hold"):
        asset.collateral_status = "incident_hold"
    item = Incident(org_id=org_id, reported_by_user_id=actor_id, **data.model_dump())
    session.add(item)
    _add_collateral_event(
        session, org_id, data.application_id, actor_id, "incident", "Incident reported", data.description
    )
    await session.flush()
    return item


async def get_application_detail(session: AsyncSession, org_id: UUID, application_id: UUID) -> ApplicationDetail:
    application = await get_application(session, org_id, application_id)
    branch = await session.scalar(select(Branch).where(Branch.id == application.branch_id, Branch.org_id == org_id))
    borrower = await session.scalar(
        select(Borrower).where(Borrower.id == application.borrower_id, Borrower.org_id == org_id)
    )
    asset = await _get_asset(session, org_id, application.id)
    product = await session.scalar(
        select(LoanProduct).where(LoanProduct.id == application.product_id, LoanProduct.org_id == org_id)
    )
    evidence = list(
        await session.scalars(
            select(EvidenceFile).where(EvidenceFile.org_id == org_id, EvidenceFile.application_id == application.id)
        )
    )
    appraisals = list(
        await session.scalars(
            select(HumanAppraisal)
            .where(HumanAppraisal.org_id == org_id, HumanAppraisal.application_id == application.id)
            .order_by(HumanAppraisal.revision)
        )
    )
    offers = list(
        await session.scalars(
            select(Offer).where(Offer.org_id == org_id, Offer.application_id == application.id).order_by(Offer.version)
        )
    )
    pickup = await session.scalar(
        select(PickupTask).where(PickupTask.org_id == org_id, PickupTask.application_id == application.id)
    )
    loan = await session.scalar(
        select(LoanAccount).where(LoanAccount.org_id == org_id, LoanAccount.application_id == application.id)
    )
    incidents = list(
        await session.scalars(
            select(Incident).where(Incident.org_id == org_id, Incident.application_id == application.id)
        )
    )
    history = list(
        await session.scalars(
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.org_id == org_id, ApplicationStatusHistory.application_id == application.id)
            .order_by(ApplicationStatusHistory.created_at)
        )
    )
    return ApplicationDetail(
        id=application.id,
        application_no=application.application_no,
        status=application.status,
        priority=application.priority,
        branch={"id": branch.id, "code": branch.code, "name": branch.name} if branch else {},
        product={"id": product.id, "code": product.code, "name": product.name} if product else None,
        borrower={
            "id": borrower.id,
            "customer_reference": borrower.customer_reference,
            "full_name": borrower.full_name,
            "phone_masked": borrower.phone_masked,
        }
        if borrower
        else {},
        asset={
            "id": asset.id,
            "asset_code": asset.asset_code,
            "category": asset.category,
            "brand": asset.brand,
            "model": asset.model,
            "condition_grade": asset.condition_grade,
            "indicative_value": asset.indicative_value,
            "collateral_status": asset.collateral_status,
        },
        requested_amount=application.requested_amount,
        requested_tenor_days=application.requested_tenor_days,
        purpose=application.purpose,
        submitted_at=application.submitted_at,
        evidence=[
            {"id": item.id, "type": item.evidence_type, "file_name": item.file_name, "scan_status": item.scan_status}
            for item in evidence
        ],
        appraisals=[
            {
                "id": item.id,
                "revision": item.revision,
                "market_value": item.market_value,
                "liquidation_value": item.liquidation_value,
                "recommended_loan": item.recommended_loan,
                "condition_grade": item.condition_grade,
                "rationale": item.rationale,
            }
            for item in appraisals
        ],
        offers=[
            {
                "id": item.id,
                "version": item.version,
                "principal_amount": item.principal_amount,
                "tenor_days": item.tenor_days,
                "total_due_amount": item.total_due_amount,
                "expires_at": item.expires_at,
                "status": item.status,
            }
            for item in offers
        ],
        pickup={
            "id": pickup.id,
            "status": pickup.status,
            "scheduled_at": pickup.scheduled_at,
            "pickup_address": pickup.pickup_address,
            "assignment_code": pickup.assignment_code,
        }
        if pickup
        else None,
        loan={
            "id": loan.id,
            "account_no": loan.account_no,
            "status": loan.status,
            "principal_amount": loan.principal_amount,
            "total_due_amount": loan.total_due_amount,
            "due_at": loan.due_at,
        }
        if loan
        else None,
        incidents=[
            {"id": item.id, "type": item.incident_type, "severity": item.severity, "status": item.status}
            for item in incidents
        ],
        history=[
            {
                "id": item.id,
                "from_status": item.from_status,
                "to_status": item.to_status,
                "note": item.note,
                "created_at": item.created_at,
            }
            for item in history
        ],
    )


async def get_collateral_timeline(session: AsyncSession, org_id: UUID, application_id: UUID) -> CollateralTimeline:
    application = await get_application(session, org_id, application_id)
    asset = await _get_asset(session, org_id, application_id)
    events = list(
        await session.scalars(
            select(CollateralEvent)
            .where(CollateralEvent.org_id == org_id, CollateralEvent.application_id == application_id)
            .order_by(CollateralEvent.occurred_at)
        )
    )
    return CollateralTimeline(
        application_id=application.id,
        application_no=application.application_no,
        asset_code=asset.asset_code,
        collateral_status=asset.collateral_status,
        events=[
            {
                "id": item.id,
                "event_type": item.event_type,
                "title": item.title,
                "description": item.description,
                "metadata": item.event_metadata,
                "occurred_at": item.occurred_at,
            }
            for item in events
        ],
    )


async def _get_asset(session: AsyncSession, org_id: UUID, application_id: UUID) -> Asset:
    asset = await session.scalar(select(Asset).where(Asset.org_id == org_id, Asset.application_id == application_id))
    if asset is None:
        raise _not_found("Collateral asset")
    return asset


def _set_collateral_status(asset: Asset, target: str) -> None:
    if not can_transition(COLLATERAL_TRANSITIONS, asset.collateral_status, target):
        raise _conflict(f"Cannot transition collateral from {asset.collateral_status} to {target}")
    asset.collateral_status = target


def _add_collateral_event(
    session: AsyncSession,
    org_id: UUID,
    application_id: UUID,
    actor_id: UUID,
    event_type: str,
    title: str,
    description: str | None = None,
    event_metadata: dict[str, object] | None = None,
) -> None:
    session.add(
        CollateralEvent(
            org_id=org_id,
            application_id=application_id,
            actor_user_id=actor_id,
            event_type=event_type,
            title=title,
            description=description,
            event_metadata=event_metadata or {},
        )
    )


async def _flush_or_conflict(session: AsyncSession, message: str) -> None:
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise _conflict(message) from exc
