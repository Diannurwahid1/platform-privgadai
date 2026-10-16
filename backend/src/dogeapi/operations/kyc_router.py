"""Customer KYC endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from dogeapi.deps import OrgIdDep, SessionDep, SettingsDep, UserDep
from dogeapi.models import Borrower, KycVerification, LoanApplication
from dogeapi.operations import kyc_service, mvp_service
from dogeapi.operations.erp_schemas import ERPActionResult
from dogeapi.operations.kyc_schemas import KycCreate, KycReview
from dogeapi.security import require_scope

router = APIRouter(prefix="/v1/customers", tags=["customer-kyc"], dependencies=[Depends(require_scope("org:read"))])
queue_router = APIRouter(prefix="/v1/kyc", tags=["customer-kyc"], dependencies=[Depends(require_scope("org:read"))])


@queue_router.get("/verifications")
async def kyc_verification_queue(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    branch_ids = await mvp_service.visible_branch_ids(
        session, org_id, user.id, {"ops_admin", "branch_manager", "loan_officer", "reviewer", "auditor"}
    )
    statement = (
        select(KycVerification, Borrower)
        .join(Borrower, (Borrower.id == KycVerification.borrower_id) & (Borrower.org_id == org_id))
        .where(KycVerification.org_id == org_id)
    )
    if branch_ids is not None:
        visible_customers = select(LoanApplication.borrower_id).where(
            LoanApplication.org_id == org_id,
            LoanApplication.branch_id.in_(branch_ids),
        )
        statement = statement.where(KycVerification.borrower_id.in_(visible_customers))
    rows = (await session.execute(statement.order_by(KycVerification.created_at.desc()).limit(500))).all()
    return [
        {
            "id": item.id,
            "customer_id": borrower.id,
            "customer_reference": borrower.customer_reference,
            "customer_name": borrower.full_name,
            "national_id_masked": item.national_id_masked,
            "status": item.status,
            "risk_level": item.risk_level,
            "verification_method": item.verification_method,
            "initiated_by_user_id": item.initiated_by_user_id,
            "reviewed_by_user_id": item.reviewed_by_user_id,
            "created_at": item.created_at,
            "reviewed_at": item.reviewed_at,
            "expires_at": item.expires_at,
        }
        for item, borrower in rows
    ]


@router.get("/{customer_id}/kyc")
async def get_customer_kyc(
    customer_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    await mvp_service.ensure_customer_access(
        session,
        org_id,
        user.id,
        customer_id,
        {"ops_admin", "branch_manager", "loan_officer", "reviewer", "auditor"},
    )
    return await kyc_service.serialize_customer_kyc(session, org_id, customer_id)


@router.post(
    "/{customer_id}/kyc", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_scope("org:write"))]
)
async def start_customer_kyc(
    customer_id: UUID, data: KycCreate, session: SessionDep, settings: SettingsDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    await mvp_service.ensure_customer_access(
        session,
        org_id,
        user.id,
        customer_id,
        {"ops_admin", "branch_manager", "loan_officer", "reviewer"},
    )
    item = await kyc_service.create_verification(session, settings, org_id, user.id, customer_id, data)
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Data KTP direkam; unggah bukti untuk pemeriksaan"}


@router.post(
    "/{customer_id}/kyc/{verification_id}/documents",
    response_model=ERPActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope("org:write"))],
)
async def upload_kyc_document(
    customer_id: UUID,
    verification_id: UUID,
    session: SessionDep,
    settings: SettingsDep,
    org_id: OrgIdDep,
    user: UserDep,
    document_side: Annotated[str, Form(pattern="^(ktp_front|selfie|supporting_document)$")],
    file: Annotated[UploadFile, File()],
) -> ERPActionResult:
    await mvp_service.ensure_customer_access(
        session,
        org_id,
        user.id,
        customer_id,
        {"ops_admin", "branch_manager", "loan_officer", "reviewer"},
    )
    allowed = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if file.content_type not in allowed:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Dokumen harus berupa JPEG, PNG, WebP, atau PDF")
    content = await file.read(10 * 1024 * 1024 + 1)
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Dokumen kosong")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Dokumen melebihi 10 MB")
    item = await kyc_service.store_document(
        session,
        settings,
        org_id,
        user.id,
        customer_id,
        verification_id,
        document_side,
        file.filename or "document",
        file.content_type or "application/octet-stream",
        content,
    )
    await session.commit()
    return ERPActionResult(
        id=item.id,
        status=item.scan_status,
        message="Dokumen KYC terenkripsi dan lulus pemindaian"
        if item.scan_status == "clean"
        else "Dokumen KYC terenkripsi tetapi dikarantina",
    )


@router.post("/{customer_id}/kyc/{verification_id}/review", dependencies=[Depends(require_scope("org:write"))])
async def review_customer_kyc(
    customer_id: UUID, verification_id: UUID, data: KycReview, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    await mvp_service.ensure_customer_access(
        session, org_id, user.id, customer_id, {"ops_admin", "branch_manager", "reviewer"}
    )
    item = await kyc_service.review_verification(session, org_id, user.id, customer_id, verification_id, data)
    await session.commit()
    return {"id": item.id, "status": item.status, "message": "Keputusan KYC tercatat"}
