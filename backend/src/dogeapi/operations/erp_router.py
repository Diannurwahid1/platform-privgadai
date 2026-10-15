"""Pawn ERP finance, collection, inventory, and reporting endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from dogeapi.deps import OrgIdDep, SessionDep, UserDep
from dogeapi.models import (
    Borrower,
    Cashbox,
    DebtorProfile,
    InventoryCheck,
    RegulatoryReportRun,
    RegulatoryReportTemplate,
    TellerSession,
)
from dogeapi.operations import erp_service, mvp_service
from dogeapi.operations.erp_schemas import (
    CashboxFundInput,
    CollectionNoteCreate,
    ERPActionResult,
    FinanceOverview,
    FinancialReports,
    InventoryCheckCreate,
    InventoryCheckSubmit,
    JournalReverseInput,
    RegulatoryRunCreate,
    RegulatoryTemplateCreate,
    TellerSessionClose,
    TellerSessionOpen,
)
from dogeapi.security import require_scope

router = APIRouter(prefix="/v1", tags=["privgadai-erp"], dependencies=[Depends(require_scope("org:read"))])


@router.get("/customers")
async def customers(session: SessionDep, org_id: OrgIdDep) -> list[dict[str, object]]:
    rows = (
        await session.execute(
            select(Borrower, DebtorProfile)
            .join(
                DebtorProfile,
                (DebtorProfile.borrower_id == Borrower.id) & (DebtorProfile.org_id == org_id),
                isouter=True,
            )
            .where(Borrower.org_id == org_id)
            .order_by(Borrower.created_at.desc())
        )
    ).all()
    return [
        {
            "id": borrower.id,
            "customer_reference": borrower.customer_reference,
            "full_name": borrower.full_name,
            "phone_masked": borrower.phone_masked,
            "dati_ii_code": profile.dati_ii_code if profile else None,
            "slik_subject_code": profile.slik_subject_code if profile else None,
            "risk_status": profile.risk_status if profile else "normal",
            "internal_watchlist": profile.internal_watchlist if profile else False,
            "correction_status": profile.correction_status if profile else "none",
        }
        for borrower, profile in rows
    ]


@router.get("/finance/overview", response_model=FinanceOverview)
async def finance_overview(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> FinanceOverview:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "branch_manager", "finance"})
    return await erp_service.finance_overview(session, org_id)


@router.get("/finance/cashboxes")
async def cashboxes(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "branch_manager", "finance"})
    rows = list(await session.scalars(select(Cashbox).where(Cashbox.org_id == org_id).order_by(Cashbox.code)))
    return [
        {"id": item.id, "branch_id": item.branch_id, "code": item.code, "name": item.name, "balance": item.balance}
        for item in rows
    ]


@router.post(
    "/finance/cashboxes/{cashbox_id}/fund",
    response_model=ERPActionResult,
    dependencies=[Depends(require_scope("org:finance:use"))],
)
async def fund_cashbox(
    cashbox_id: UUID, data: CashboxFundInput, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "finance"})
    item = await erp_service.fund_cashbox(
        session, org_id, user.id, cashbox_id, data.amount, data.external_reference, data.idempotency_key
    )
    await session.commit()
    return ERPActionResult(id=item.id, status="posted", message="Cash funding posted to cashbook and general ledger")


@router.post(
    "/finance/teller-sessions",
    response_model=ERPActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope("org:finance:use"))],
)
async def open_teller_session(
    data: TellerSessionOpen, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "finance"})
    item = await erp_service.open_teller_session(session, org_id, user.id, data.cashbox_id)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Teller session opened")


@router.post(
    "/finance/teller-sessions/{session_id}/close",
    response_model=ERPActionResult,
    dependencies=[Depends(require_scope("org:finance:use"))],
)
async def close_teller_session(
    session_id: UUID,
    data: TellerSessionClose,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "finance"})
    item = await erp_service.close_teller_session(session, org_id, user.id, session_id, data.actual_closing_balance)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Teller session closed and reconciled")


@router.get("/finance/teller-sessions")
async def teller_sessions(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "branch_manager", "finance"})
    rows = list(
        await session.scalars(
            select(TellerSession)
            .where(TellerSession.org_id == org_id)
            .order_by(TellerSession.opened_at.desc())
            .limit(50)
        )
    )
    return [
        {
            "id": item.id,
            "cashbox_id": item.cashbox_id,
            "teller_user_id": item.teller_user_id,
            "status": item.status,
            "opening_balance": item.opening_balance,
            "expected_closing_balance": item.expected_closing_balance,
            "actual_closing_balance": item.actual_closing_balance,
            "opened_at": item.opened_at,
            "closed_at": item.closed_at,
        }
        for item in rows
    ]


@router.get("/accounting/reports", response_model=FinancialReports)
async def accounting_reports(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> FinancialReports:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "finance", "auditor"}
    )
    return await erp_service.financial_reports(session, org_id)


@router.post(
    "/accounting/journals/{journal_id}/reverse",
    response_model=ERPActionResult,
    dependencies=[Depends(require_scope("org:finance:use"))],
)
async def reverse_journal(
    journal_id: UUID,
    data: JournalReverseInput,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "finance"})
    item = await erp_service.reverse_journal(session, org_id, user.id, journal_id, data.reason, data.idempotency_key)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Balanced reversal journal posted")


@router.get("/collections")
async def collections(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "loan_officer", "finance"}
    )
    return await erp_service.list_collections(session, org_id)


@router.post(
    "/collections/{case_id}/notes",
    response_model=ERPActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope("org:collections:use"))],
)
async def collection_note(
    case_id: UUID, data: CollectionNoteCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "loan_officer", "finance"}
    )
    item = await erp_service.add_collection_note(session, org_id, user.id, case_id, data)
    await session.commit()
    return ERPActionResult(id=item.id, status="recorded", message="Collection follow-up recorded")


@router.get("/regulatory/templates")
async def regulatory_templates(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "finance", "auditor"}
    )
    rows = list(
        await session.scalars(
            select(RegulatoryReportTemplate)
            .where(RegulatoryReportTemplate.org_id == org_id)
            .order_by(RegulatoryReportTemplate.report_type, RegulatoryReportTemplate.code)
        )
    )
    return [
        {
            "id": item.id,
            "report_type": item.report_type,
            "code": item.code,
            "name": item.name,
            "version": item.version,
            "effective_from": item.effective_from,
            "status": item.status,
        }
        for item in rows
    ]


@router.post(
    "/regulatory/templates",
    response_model=ERPActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope("org:master:write"))],
)
async def create_regulatory_template(
    data: RegulatoryTemplateCreate, session: SessionDep, org_id: OrgIdDep
) -> ERPActionResult:
    item = await erp_service.create_regulatory_template(session, org_id, data)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Versioned regulatory template created")


@router.get("/regulatory/runs")
async def regulatory_runs(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "finance", "auditor"}
    )
    rows = list(
        await session.scalars(
            select(RegulatoryReportRun)
            .where(RegulatoryReportRun.org_id == org_id)
            .order_by(RegulatoryReportRun.created_at.desc())
        )
    )
    return [
        {
            "id": item.id,
            "template_id": item.template_id,
            "period_start": item.period_start,
            "period_end": item.period_end,
            "revision": item.revision,
            "status": item.status,
            "validation_results": item.validation_results,
            "report_payload": item.report_payload,
        }
        for item in rows
    ]


@router.post(
    "/regulatory/runs",
    response_model=ERPActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope("org:reports:read"))],
)
async def create_regulatory_run(
    data: RegulatoryRunCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "finance", "auditor"}
    )
    item = await erp_service.create_regulatory_run(session, org_id, user.id, data)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Regulatory report draft generated; not submitted")


@router.get("/inventory-checks")
async def inventory_checks(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "custodian", "auditor"}
    )
    rows = list(
        await session.scalars(
            select(InventoryCheck).where(InventoryCheck.org_id == org_id).order_by(InventoryCheck.counted_at.desc())
        )
    )
    return [
        {
            "id": item.id,
            "location_id": item.location_id,
            "performed_by_user_id": item.performed_by_user_id,
            "reviewed_by_user_id": item.reviewed_by_user_id,
            "status": item.status,
            "counted_at": item.counted_at,
            "approved_at": item.approved_at,
        }
        for item in rows
    ]


@router.post(
    "/inventory-checks",
    response_model=ERPActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope("org:inventory:use"))],
)
async def create_inventory_check(
    data: InventoryCheckCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "custodian"}
    )
    item = await erp_service.create_inventory_check(session, org_id, user.id, data.location_id)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Stock opname started")


@router.post(
    "/inventory-checks/{check_id}/submit",
    response_model=ERPActionResult,
    dependencies=[Depends(require_scope("org:inventory:use"))],
)
async def submit_inventory_check(
    check_id: UUID,
    data: InventoryCheckSubmit,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "custodian"}
    )
    item = await erp_service.submit_inventory_check(session, org_id, check_id, data)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Stock opname submitted for review")


@router.post(
    "/inventory-checks/{check_id}/approve",
    response_model=ERPActionResult,
    dependencies=[Depends(require_scope("org:inventory:use"))],
)
async def approve_inventory_check(
    check_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "branch_manager", "auditor"})
    item = await erp_service.approve_inventory_check(session, org_id, user.id, check_id)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Stock opname approved by checker")
