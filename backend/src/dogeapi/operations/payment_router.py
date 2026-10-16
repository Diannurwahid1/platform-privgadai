"""Payment ledger, controlled adjustment, and reconciliation endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from dogeapi.deps import OrgIdDep, SessionDep, UserDep
from dogeapi.operations import payment_service
from dogeapi.operations.payment_schemas import (
    PaymentActionResult,
    PaymentAdjustmentCreate,
    PaymentCreate,
    ReconciliationCreate,
    ReconciliationResolve,
)
from dogeapi.security import require_scope

router = APIRouter(prefix="/v1/finance", tags=["payment-control"], dependencies=[Depends(require_scope("org:read"))])
write_access = Depends(require_scope("org:write"))


@router.get("/payments")
async def payments(session: SessionDep, org_id: OrgIdDep) -> list[dict[str, object]]:
    return await payment_service.list_receipts(session, org_id)


@router.get("/loan-accounts")
async def loan_accounts(session: SessionDep, org_id: OrgIdDep) -> list[dict[str, object]]:
    return await payment_service.list_payment_accounts(session, org_id)


@router.post(
    "/payments", response_model=PaymentActionResult, status_code=status.HTTP_201_CREATED, dependencies=[write_access]
)
async def create_payment(
    data: PaymentCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> PaymentActionResult:
    item = await payment_service.record_payment(session, org_id, user.id, data)
    await session.commit()
    return PaymentActionResult(id=item.id, status=item.status, message=f"Receipt {item.receipt_no} berhasil diposting")


@router.get("/payment-adjustments")
async def adjustments(session: SessionDep, org_id: OrgIdDep) -> list[dict[str, object]]:
    return await payment_service.list_adjustments(session, org_id)


@router.post(
    "/payment-adjustments",
    response_model=PaymentActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[write_access],
)
async def create_adjustment(
    data: PaymentAdjustmentCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> PaymentActionResult:
    item = await payment_service.request_adjustment(session, org_id, user.id, data)
    await session.commit()
    return PaymentActionResult(id=item.id, status=item.status, message="Adjustment dikirim ke checker independen")


@router.get("/reconciliations")
async def reconciliations(session: SessionDep, org_id: OrgIdDep) -> list[dict[str, object]]:
    return await payment_service.list_reconciliations(session, org_id)


@router.post(
    "/reconciliations",
    response_model=PaymentActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[write_access],
)
async def create_reconciliation(
    data: ReconciliationCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> PaymentActionResult:
    item = await payment_service.create_reconciliation(session, org_id, user.id, data)
    await session.commit()
    return PaymentActionResult(id=item.id, status=item.status, message="Reconciliation snapshot berhasil dibuat")


@router.post("/reconciliations/{run_id}/resolution", response_model=PaymentActionResult, dependencies=[write_access])
async def resolve_reconciliation(
    run_id: UUID, data: ReconciliationResolve, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> PaymentActionResult:
    item = await payment_service.request_reconciliation_resolution(
        session, org_id, user.id, run_id, data.resolution_note
    )
    await session.commit()
    return PaymentActionResult(id=item.id, status=item.status, message="Resolusi exception menunggu approval")
