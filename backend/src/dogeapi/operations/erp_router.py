"""Pawn ERP finance, collection, inventory, and reporting endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select

from dogeapi.deps import OrgIdDep, SessionDep, SettingsDep, UserDep
from dogeapi.models import (
    AccountingPeriod,
    ApplicationStatusHistory,
    ApprovalEvent,
    ApprovalRequest,
    Asset,
    Borrower,
    Branch,
    Cashbox,
    CashTransaction,
    CollateralEvent,
    CollectionCase,
    Consent,
    DebtorProfile,
    InventoryCheck,
    InventoryCheckItem,
    KycEvent,
    KycVerification,
    LoanAccount,
    LoanApplication,
    RegulatoryReportRun,
    RegulatoryReportTemplate,
    TellerSession,
)
from dogeapi.operations import erp_service, mvp_service
from dogeapi.operations.erp_schemas import (
    AccountingPeriodCreate,
    ApprovalSubmitInput,
    CashboxFundInput,
    CollectionCasePlanUpdate,
    CollectionNoteCreate,
    CollectionPromiseCreate,
    CollectionPromiseResolve,
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


@router.get("/customers/{customer_id}")
async def customer_detail(customer_id: UUID, session: SessionDep, org_id: OrgIdDep) -> dict[str, object]:
    """Return a tenant-scoped customer view for operational CRM."""
    row = (
        await session.execute(
            select(Borrower, DebtorProfile)
            .join(
                DebtorProfile,
                (DebtorProfile.borrower_id == Borrower.id) & (DebtorProfile.org_id == org_id),
                isouter=True,
            )
            .where(Borrower.org_id == org_id, Borrower.id == customer_id)
        )
    ).one_or_none()
    if row is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debitur tidak ditemukan")

    borrower, profile = row
    application_rows = (
        await session.execute(
            select(LoanApplication, Branch, Asset, LoanAccount)
            .join(Branch, (Branch.id == LoanApplication.branch_id) & (Branch.org_id == org_id))
            .join(
                Asset,
                (Asset.application_id == LoanApplication.id) & (Asset.org_id == org_id),
                isouter=True,
            )
            .join(
                LoanAccount,
                (LoanAccount.application_id == LoanApplication.id) & (LoanAccount.org_id == org_id),
                isouter=True,
            )
            .where(LoanApplication.org_id == org_id, LoanApplication.borrower_id == customer_id)
            .order_by(LoanApplication.created_at.desc())
        )
    ).all()
    application_ids = [application.id for application, _, _, _ in application_rows]
    loan_ids = [loan.id for _, _, _, loan in application_rows if loan is not None]

    consents = list(
        await session.scalars(
            select(Consent)
            .where(Consent.org_id == org_id, Consent.borrower_id == customer_id)
            .order_by(Consent.accepted_at.desc())
        )
    )
    histories = []
    if application_ids:
        histories = list(
            await session.scalars(
                select(ApplicationStatusHistory)
                .where(
                    ApplicationStatusHistory.org_id == org_id,
                    ApplicationStatusHistory.application_id.in_(application_ids),
                )
                .order_by(ApplicationStatusHistory.created_at.desc())
                .limit(100)
            )
        )
    collection_cases = []
    if loan_ids:
        collection_cases = list(
            await session.scalars(
                select(CollectionCase)
                .where(CollectionCase.org_id == org_id, CollectionCase.loan_account_id.in_(loan_ids))
                .order_by(CollectionCase.created_at.desc())
            )
        )

    applications = [
        {
            "id": application.id,
            "application_no": application.application_no,
            "status": application.status,
            "priority": application.priority,
            "branch_code": branch.code,
            "branch_name": branch.name,
            "requested_amount": application.requested_amount,
            "submitted_at": application.submitted_at,
            "asset": (
                {
                    "id": asset.id,
                    "asset_code": asset.asset_code,
                    "category": asset.category,
                    "label": " ".join(part for part in (asset.brand, asset.model) if part) or asset.category,
                    "collateral_status": asset.collateral_status,
                    "indicative_value": asset.indicative_value,
                }
                if asset
                else None
            ),
            "loan": (
                {
                    "id": loan.id,
                    "account_no": loan.account_no,
                    "status": loan.status,
                    "principal_amount": loan.principal_amount,
                    "outstanding_principal": loan.outstanding_principal,
                    "outstanding_fee": loan.outstanding_fee,
                    "paid_amount": loan.paid_amount,
                    "due_at": loan.due_at,
                }
                if loan
                else None
            ),
        }
        for application, branch, asset, loan in application_rows
    ]
    total_outstanding = sum(
        (loan.outstanding_principal + loan.outstanding_fee for _, _, _, loan in application_rows if loan is not None),
        start=0,
    )

    return {
        "id": borrower.id,
        "customer_reference": borrower.customer_reference,
        "full_name": borrower.full_name,
        "phone_masked": borrower.phone_masked,
        "created_at": borrower.created_at,
        "profile": {
            "national_id_masked": profile.national_id_masked if profile else None,
            "dati_ii_code": profile.dati_ii_code if profile else None,
            "slik_subject_code": profile.slik_subject_code if profile else None,
            "risk_status": profile.risk_status if profile else "normal",
            "risk_notes": profile.risk_notes if profile else None,
            "internal_watchlist": profile.internal_watchlist if profile else False,
            "watchlist_reason": profile.watchlist_reason if profile else None,
            "correction_status": profile.correction_status if profile else "none",
        },
        "summary": {
            "application_count": len(applications),
            "active_loan_count": sum(1 for item in applications if item["loan"] and item["loan"]["status"] == "active"),
            "collateral_count": sum(1 for item in applications if item["asset"] is not None),
            "total_outstanding": total_outstanding,
            "open_collection_count": sum(1 for case in collection_cases if case.status not in {"resolved", "closed"}),
        },
        "applications": applications,
        "consents": [
            {
                "id": consent.id,
                "consent_type": consent.consent_type,
                "document_version": consent.document_version,
                "channel": consent.channel,
                "accepted_at": consent.accepted_at,
            }
            for consent in consents
        ],
        "collections": [
            {
                "id": case.id,
                "loan_account_id": case.loan_account_id,
                "aging_bucket": case.aging_bucket,
                "status": case.status,
                "outstanding_amount": case.outstanding_amount,
                "due_at": case.due_at,
                "next_action_at": case.next_action_at,
            }
            for case in collection_cases
        ],
        "activity": [
            {
                "id": history.id,
                "application_id": history.application_id,
                "from_status": history.from_status,
                "to_status": history.to_status,
                "note": history.note,
                "occurred_at": history.created_at,
            }
            for history in histories
        ],
    }


@router.get("/domain-events")
async def domain_events(session: SessionDep, org_id: OrgIdDep, limit: int = 200) -> list[dict[str, object]]:
    """Build an auditor-friendly business event feed from append-only operational records."""
    safe_limit = min(max(limit, 1), 500)
    status_rows = (
        await session.execute(
            select(ApplicationStatusHistory, LoanApplication)
            .join(
                LoanApplication,
                (LoanApplication.id == ApplicationStatusHistory.application_id) & (LoanApplication.org_id == org_id),
            )
            .where(ApplicationStatusHistory.org_id == org_id)
            .order_by(ApplicationStatusHistory.created_at.desc())
            .limit(safe_limit)
        )
    ).all()
    collateral_rows = (
        await session.execute(
            select(CollateralEvent, LoanApplication)
            .join(
                LoanApplication,
                (LoanApplication.id == CollateralEvent.application_id) & (LoanApplication.org_id == org_id),
            )
            .where(CollateralEvent.org_id == org_id)
            .order_by(CollateralEvent.occurred_at.desc())
            .limit(safe_limit)
        )
    ).all()
    cash_rows = list(
        await session.scalars(
            select(CashTransaction)
            .where(CashTransaction.org_id == org_id)
            .order_by(CashTransaction.occurred_at.desc())
            .limit(safe_limit)
        )
    )
    report_rows = list(
        await session.scalars(
            select(RegulatoryReportRun)
            .where(RegulatoryReportRun.org_id == org_id)
            .order_by(RegulatoryReportRun.created_at.desc())
            .limit(safe_limit)
        )
    )
    kyc_rows = (
        await session.execute(
            select(KycEvent, KycVerification, Borrower)
            .join(
                KycVerification, (KycVerification.id == KycEvent.verification_id) & (KycVerification.org_id == org_id)
            )
            .join(Borrower, (Borrower.id == KycVerification.borrower_id) & (Borrower.org_id == org_id))
            .where(KycEvent.org_id == org_id)
            .order_by(KycEvent.occurred_at.desc())
            .limit(safe_limit)
        )
    ).all()
    approval_rows = (
        await session.execute(
            select(ApprovalEvent, ApprovalRequest)
            .join(
                ApprovalRequest, (ApprovalRequest.id == ApprovalEvent.approval_id) & (ApprovalRequest.org_id == org_id)
            )
            .where(ApprovalEvent.org_id == org_id)
            .order_by(ApprovalEvent.occurred_at.desc())
            .limit(safe_limit)
        )
    ).all()

    events: list[dict[str, object]] = []
    for history, application in status_rows:
        events.append(
            {
                "id": history.id,
                "event_type": "ApplicationStateChanged",
                "category": "loan",
                "title": f"Status {application.application_no} berubah menjadi {history.to_status}",
                "description": history.note or "Perubahan tahap proses pengajuan",
                "aggregate_type": "application",
                "aggregate_id": application.id,
                "aggregate_reference": application.application_no,
                "actor_id": history.actor_user_id,
                "occurred_at": history.created_at,
                "metadata": {"from_status": history.from_status, "to_status": history.to_status},
            }
        )
    for event, application in collateral_rows:
        events.append(
            {
                "id": event.id,
                "event_type": event.event_type,
                "category": "collateral",
                "title": event.title,
                "description": event.description or "Aktivitas chain of custody",
                "aggregate_type": "application",
                "aggregate_id": application.id,
                "aggregate_reference": application.application_no,
                "actor_id": event.actor_user_id,
                "occurred_at": event.occurred_at,
                "metadata": event.event_metadata,
            }
        )
    for transaction in cash_rows:
        events.append(
            {
                "id": transaction.id,
                "event_type": "CashTransactionPosted",
                "category": "finance",
                "title": f"Transaksi kas {transaction.transaction_type} diposting",
                "description": f"{transaction.direction} {transaction.amount} · ref {transaction.external_reference}",
                "aggregate_type": "cash_transaction",
                "aggregate_id": transaction.id,
                "aggregate_reference": transaction.external_reference,
                "actor_id": None,
                "occurred_at": transaction.occurred_at,
                "metadata": {
                    "cashbox_id": str(transaction.cashbox_id),
                    "loan_account_id": str(transaction.loan_account_id) if transaction.loan_account_id else None,
                    "journal_entry_id": str(transaction.journal_entry_id),
                    "amount": str(transaction.amount),
                    "direction": transaction.direction,
                },
            }
        )
    for run in report_rows:
        events.append(
            {
                "id": run.id,
                "event_type": "RegulatoryReportRunCreated",
                "category": "regulatory",
                "title": f"Report run periode {run.period_start} — {run.period_end}",
                "description": f"Revision {run.revision} · status {run.status}",
                "aggregate_type": "regulatory_report_run",
                "aggregate_id": run.id,
                "aggregate_reference": f"{run.period_start}/{run.period_end}",
                "actor_id": run.generated_by_user_id,
                "occurred_at": run.created_at,
                "metadata": {"template_id": str(run.template_id), "revision": run.revision, "status": run.status},
            }
        )
    for event, verification, borrower in kyc_rows:
        events.append(
            {
                "id": event.id,
                "event_type": event.event_type,
                "category": "customer",
                "title": f"KYC {borrower.customer_reference} berubah menjadi {event.to_status}",
                "description": event.reason or "Pemeriksaan identitas nasabah",
                "aggregate_type": "customer",
                "aggregate_id": borrower.id,
                "aggregate_reference": borrower.customer_reference,
                "actor_id": event.actor_user_id,
                "occurred_at": event.occurred_at,
                "metadata": {
                    "verification_id": str(verification.id),
                    "from_status": event.from_status,
                    "to_status": event.to_status,
                    "risk_level": verification.risk_level,
                    "document_type": verification.document_type,
                },
            }
        )
    for event, approval in approval_rows:
        events.append(
            {
                "id": event.id,
                "event_type": event.event_type,
                "category": "approval",
                "title": f"Approval {approval.aggregate_reference} menjadi {event.to_status}",
                "description": event.reason or approval.request_reason,
                "aggregate_type": "approval",
                "aggregate_id": approval.id,
                "aggregate_reference": approval.aggregate_reference,
                "actor_id": event.actor_user_id,
                "occurred_at": event.occurred_at,
                "metadata": {
                    "action": approval.action,
                    "target_type": approval.aggregate_type,
                    "target_id": str(approval.aggregate_id),
                    "from_status": event.from_status,
                    "to_status": event.to_status,
                },
            }
        )
    events.sort(key=lambda item: item["occurred_at"], reverse=True)
    return events[:safe_limit]


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
    item = await erp_service.close_teller_session(
        session,
        org_id,
        user.id,
        session_id,
        data.actual_closing_balance,
        data.variance_reason,
    )
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
            "variance_amount": item.variance_amount,
            "variance_reason": item.variance_reason,
            "variance_approved_by_user_id": item.variance_approved_by_user_id,
            "variance_approved_at": item.variance_approved_at,
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


@router.get("/accounting/journals")
async def accounting_journals(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "finance", "auditor"}
    )
    return await erp_service.list_journals(session, org_id)


@router.get("/accounting/periods")
async def accounting_periods(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "finance", "auditor"}
    )
    rows = list(
        await session.scalars(
            select(AccountingPeriod)
            .where(AccountingPeriod.org_id == org_id)
            .order_by(AccountingPeriod.period_start.desc())
        )
    )
    return [
        {
            "id": item.id,
            "period_start": item.period_start,
            "period_end": item.period_end,
            "status": item.status,
            "close_reason": item.close_reason,
            "closed_by_user_id": item.closed_by_user_id,
            "closed_at": item.closed_at,
        }
        for item in rows
    ]


@router.post("/accounting/periods", response_model=ERPActionResult, status_code=status.HTTP_201_CREATED)
async def create_accounting_period(
    data: AccountingPeriodCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "finance"})
    item = await erp_service.create_accounting_period(session, org_id, data)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Accounting period created")


@router.post("/accounting/periods/{period_id}/close", response_model=ERPActionResult)
async def close_accounting_period(
    period_id: UUID,
    data: ApprovalSubmitInput,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "finance"})
    item = await erp_service.request_accounting_period_close(session, org_id, user.id, period_id, data.reason)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Period close submitted for approval")


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
    item = await erp_service.request_journal_reversal(
        session, org_id, user.id, journal_id, data.reason, data.idempotency_key
    )
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Journal reversal submitted for checker approval")


@router.get("/collections")
async def collections(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "loan_officer", "finance"}
    )
    return await erp_service.list_collections(session, org_id)


@router.get("/collections/{case_id}")
async def collection_case_detail(
    case_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "loan_officer", "finance"}
    )
    return await erp_service.collection_detail(session, org_id, case_id)


@router.patch(
    "/collections/{case_id}/plan",
    response_model=ERPActionResult,
    dependencies=[Depends(require_scope("org:collections:use"))],
)
async def update_collection_case_plan(
    case_id: UUID, data: CollectionCasePlanUpdate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "loan_officer", "finance"}
    )
    item = await erp_service.update_collection_plan(
        session, org_id, case_id, data.strategy, data.stage, data.next_action_at
    )
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Collection strategy and next action updated")


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


@router.post(
    "/collections/{case_id}/promises",
    response_model=ERPActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope("org:collections:use"))],
)
async def create_promise_to_pay(
    case_id: UUID, data: CollectionPromiseCreate, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "loan_officer", "finance"}
    )
    item = await erp_service.create_collection_promise(
        session,
        org_id,
        user.id,
        case_id,
        amount=data.amount,
        promised_at=data.promised_at,
        channel=data.channel,
        note=data.note,
    )
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Promise to pay recorded")


@router.post(
    "/collections/{case_id}/promises/{promise_id}/resolve",
    response_model=ERPActionResult,
    dependencies=[Depends(require_scope("org:collections:use"))],
)
async def resolve_promise_to_pay(
    case_id: UUID,
    promise_id: UUID,
    data: CollectionPromiseResolve,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "loan_officer", "finance"}
    )
    item = await erp_service.resolve_collection_promise(
        session, org_id, user.id, case_id, promise_id, data.status, data.reason
    )
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Promise resolution recorded")


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


@router.post(
    "/regulatory/templates/{template_id}/submit-for-activation",
    response_model=ERPActionResult,
    dependencies=[Depends(require_scope("org:master:write"))],
)
async def submit_regulatory_template_activation(
    template_id: UUID,
    data: ApprovalSubmitInput,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(session, org_id, user.id, {"ops_admin", "finance", "auditor"})
    item = await erp_service.submit_regulatory_template_for_activation(
        session, org_id, user.id, template_id, data.reason
    )
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Template submitted for independent activation")


@router.get("/regulatory/runs")
async def regulatory_runs(session: SessionDep, org_id: OrgIdDep, user: UserDep) -> list[dict[str, object]]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "finance", "auditor"}
    )
    rows = (
        await session.execute(
            select(RegulatoryReportRun, RegulatoryReportTemplate)
            .join(
                RegulatoryReportTemplate,
                (RegulatoryReportTemplate.id == RegulatoryReportRun.template_id)
                & (RegulatoryReportTemplate.org_id == org_id),
            )
            .where(RegulatoryReportRun.org_id == org_id)
            .order_by(RegulatoryReportRun.created_at.desc())
        )
    ).all()
    return [
        {
            "id": item.id,
            "template_id": item.template_id,
            "report_type": template.report_type,
            "template_code": template.code,
            "template_name": template.name,
            "template_version": template.version,
            "period_start": item.period_start,
            "period_end": item.period_end,
            "revision": item.revision,
            "status": item.status,
            "validation_results": item.validation_results,
            "report_payload": item.report_payload,
            "approved_by_user_id": item.approved_by_user_id,
            "approved_at": item.approved_at,
        }
        for item, template in rows
    ]


@router.post(
    "/regulatory/runs",
    response_model=ERPActionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_scope("org:reports:read"))],
)
async def create_regulatory_run(
    data: RegulatoryRunCreate, session: SessionDep, settings: SettingsDep, org_id: OrgIdDep, user: UserDep
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "finance", "auditor"}
    )
    item = await erp_service.create_regulatory_run(session, org_id, user.id, data, settings)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Regulatory report draft generated; not submitted")


@router.post(
    "/regulatory/runs/{run_id}/submit-for-approval",
    response_model=ERPActionResult,
    dependencies=[Depends(require_scope("org:reports:read"))],
)
async def submit_regulatory_run(
    run_id: UUID,
    data: ApprovalSubmitInput,
    session: SessionDep,
    org_id: OrgIdDep,
    user: UserDep,
) -> ERPActionResult:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "finance", "auditor"}
    )
    item = await erp_service.submit_regulatory_run_for_approval(session, org_id, user.id, run_id, data.reason)
    await session.commit()
    return ERPActionResult(id=item.id, status=item.status, message="Regulatory report submitted for sign-off")


@router.get("/regulatory/runs/{run_id}/export")
async def export_regulatory_run(
    run_id: UUID, session: SessionDep, settings: SettingsDep, org_id: OrgIdDep, user: UserDep
) -> Response:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "finance", "auditor"}
    )
    content, filename, checksum = await erp_service.export_regulatory_package(session, org_id, run_id, settings)
    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-SHA256": checksum,
        },
    )


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
            "item_count": int(
                (
                    await session.scalar(
                        select(func.count(InventoryCheckItem.id)).where(
                            InventoryCheckItem.org_id == org_id,
                            InventoryCheckItem.inventory_check_id == item.id,
                        )
                    )
                )
                or 0
            ),
            "variance_count": int(
                (
                    await session.scalar(
                        select(func.count(InventoryCheckItem.id)).where(
                            InventoryCheckItem.org_id == org_id,
                            InventoryCheckItem.inventory_check_id == item.id,
                            InventoryCheckItem.result == "variance",
                        )
                    )
                )
                or 0
            ),
        }
        for item in rows
    ]


@router.get("/inventory-checks/{check_id}")
async def inventory_check_detail(
    check_id: UUID, session: SessionDep, org_id: OrgIdDep, user: UserDep
) -> dict[str, object]:
    await mvp_service.ensure_any_operational_role(
        session, org_id, user.id, {"ops_admin", "branch_manager", "custodian", "auditor"}
    )
    return await erp_service.inventory_check_detail(session, org_id, check_id)


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
    item = await erp_service.submit_inventory_check(session, org_id, user.id, check_id, data)
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
    raise HTTPException(
        status.HTTP_410_GONE,
        "Gunakan approval inbox agar keputusan stock opname memiliki snapshot, alasan, dan audit event",
    )
