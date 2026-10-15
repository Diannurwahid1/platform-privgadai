"""Integrated finance, collections, inventory, and reporting services."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    ApprovalRequest,
    Asset,
    Branch,
    Cashbox,
    CashTransaction,
    CollectionCase,
    CollectionNote,
    CustodyEvent,
    CustodyLocation,
    GLAccount,
    InventoryCheck,
    InventoryCheckItem,
    JournalEntry,
    JournalLine,
    LoanAccount,
    LoanApplication,
    LoanLedgerEntry,
    RegulatoryReportRun,
    RegulatoryReportTemplate,
    TellerSession,
)
from dogeapi.operations.erp_schemas import (
    CollectionNoteCreate,
    FinanceOverview,
    FinancialReports,
    InventoryCheckSubmit,
    RegulatoryRunCreate,
    RegulatoryTemplateCreate,
)

ACCOUNT_DEFINITIONS = (
    ("1100", "Kas dan Bank", "asset", "debit"),
    ("1200", "Piutang Pokok Gadai", "asset", "debit"),
    ("1210", "Piutang Biaya Layanan", "asset", "debit"),
    ("3100", "Modal Disetor", "equity", "credit"),
    ("4100", "Pendapatan Biaya Layanan", "income", "credit"),
)


def _not_found(label: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{label} not found")


async def ensure_finance_masters(
    session: AsyncSession, org_id: UUID, branch_id: UUID
) -> tuple[dict[str, GLAccount], Cashbox]:
    accounts = {
        account.code: account for account in await session.scalars(select(GLAccount).where(GLAccount.org_id == org_id))
    }
    for code, name, account_type, normal_balance in ACCOUNT_DEFINITIONS:
        if code not in accounts:
            account = GLAccount(
                org_id=org_id,
                code=code,
                name=name,
                account_type=account_type,
                normal_balance=normal_balance,
            )
            session.add(account)
            accounts[code] = account
    await session.flush()
    cashbox = await session.scalar(
        select(Cashbox).where(Cashbox.org_id == org_id, Cashbox.branch_id == branch_id, Cashbox.is_active)
    )
    if cashbox is None:
        branch = await session.scalar(select(Branch).where(Branch.org_id == org_id, Branch.id == branch_id))
        if branch is None:
            raise _not_found("Branch")
        cashbox = Cashbox(
            org_id=org_id,
            branch_id=branch_id,
            code=f"CASH-{branch.code}",
            name=f"Kas {branch.name}",
            balance=Decimal("0"),
        )
        session.add(cashbox)
        await session.flush()
    return accounts, cashbox


async def post_journal(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    application_id: UUID | None,
    event_type: str,
    idempotency_key: str,
    description: str,
    lines: list[tuple[GLAccount, Decimal, Decimal, str]],
) -> JournalEntry:
    existing = await session.scalar(
        select(JournalEntry).where(JournalEntry.org_id == org_id, JournalEntry.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing
    total_debit = sum((line[1] for line in lines), Decimal("0"))
    total_credit = sum((line[2] for line in lines), Decimal("0"))
    if total_debit <= 0 or total_debit != total_credit:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Journal entry must be balanced")
    entry = JournalEntry(
        org_id=org_id,
        application_id=application_id,
        entry_no=f"JE-{datetime.now(UTC).strftime('%y%m%d')}-{secrets.token_hex(4).upper()}",
        event_type=event_type,
        idempotency_key=idempotency_key,
        description=description,
        created_by_user_id=actor_id,
    )
    session.add(entry)
    await session.flush()
    session.add_all(
        [
            JournalLine(
                org_id=org_id,
                journal_entry_id=entry.id,
                account_id=account.id,
                debit_amount=debit,
                credit_amount=credit,
                description=line_description,
            )
            for account, debit, credit, line_description in lines
        ]
    )
    await session.flush()
    return entry


async def reverse_journal(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    journal_id: UUID,
    reason: str,
    idempotency_key: str,
) -> JournalEntry:
    """Create an immutable, balanced counter-entry for an accounting correction."""
    existing = await session.scalar(
        select(JournalEntry).where(JournalEntry.org_id == org_id, JournalEntry.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing
    original = await session.scalar(
        select(JournalEntry).where(JournalEntry.org_id == org_id, JournalEntry.id == journal_id)
    )
    if original is None:
        raise _not_found("Journal entry")
    if original.reversal_of_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A reversal entry cannot be reversed")
    prior_reversal = await session.scalar(
        select(JournalEntry).where(JournalEntry.org_id == org_id, JournalEntry.reversal_of_id == original.id)
    )
    if prior_reversal is not None or original.status == "reversed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Journal entry has already been reversed")
    linked_cash_transaction = await session.scalar(
        select(CashTransaction).where(
            CashTransaction.org_id == org_id,
            CashTransaction.journal_entry_id == original.id,
        )
    )
    if linked_cash_transaction is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cash transaction journals must be reversed through their source transaction workflow",
        )
    rows = (
        await session.execute(
            select(JournalLine, GLAccount)
            .join(GLAccount, (GLAccount.id == JournalLine.account_id) & (GLAccount.org_id == org_id))
            .where(JournalLine.org_id == org_id, JournalLine.journal_entry_id == original.id)
        )
    ).all()
    if not rows:
        raise HTTPException(status.HTTP_409_CONFLICT, "Journal entry has no lines")
    reversal = await post_journal(
        session,
        org_id,
        actor_id,
        original.application_id,
        "journal_reversal",
        idempotency_key,
        f"Reversal of {original.entry_no}: {reason}",
        [
            (account, line.credit_amount, line.debit_amount, f"Reversal: {line.description or original.description}")
            for line, account in rows
        ],
    )
    reversal.reversal_of_id = original.id
    original.status = "reversed"
    await session.flush()
    return reversal


async def list_journals(session: AsyncSession, org_id: UUID) -> list[dict[str, object]]:
    entries = list(
        await session.scalars(
            select(JournalEntry).where(JournalEntry.org_id == org_id).order_by(JournalEntry.posted_at.desc()).limit(200)
        )
    )
    output: list[dict[str, object]] = []
    for entry in entries:
        lines = (
            await session.execute(
                select(JournalLine, GLAccount)
                .join(GLAccount, (GLAccount.org_id == org_id) & (GLAccount.id == JournalLine.account_id))
                .where(JournalLine.org_id == org_id, JournalLine.journal_entry_id == entry.id)
                .order_by(GLAccount.code)
            )
        ).all()
        output.append(
            {
                "id": entry.id,
                "entry_no": entry.entry_no,
                "event_type": entry.event_type,
                "description": entry.description,
                "status": entry.status,
                "application_id": entry.application_id,
                "reversal_of_id": entry.reversal_of_id,
                "posted_at": entry.posted_at,
                "created_by_user_id": entry.created_by_user_id,
                "total_debit": sum((line.debit_amount for line, _ in lines), Decimal("0")),
                "total_credit": sum((line.credit_amount for line, _ in lines), Decimal("0")),
                "lines": [
                    {
                        "account_code": account.code,
                        "account_name": account.name,
                        "debit": line.debit_amount,
                        "credit": line.credit_amount,
                        "description": line.description,
                    }
                    for line, account in lines
                ],
            }
        )
    return output


async def request_journal_reversal(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    journal_id: UUID,
    reason: str,
    idempotency_key: str,
) -> ApprovalRequest:
    original = await session.scalar(
        select(JournalEntry).where(JournalEntry.org_id == org_id, JournalEntry.id == journal_id)
    )
    if original is None:
        raise _not_found("Journal entry")
    if original.reversal_of_id is not None or original.status == "reversed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Journal entry is not reversible")
    if await session.scalar(
        select(CashTransaction).where(
            CashTransaction.org_id == org_id,
            CashTransaction.journal_entry_id == original.id,
        )
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cash transaction journals must be reversed through their source transaction workflow",
        )
    branch_id = None
    if original.application_id is not None:
        branch_id = await session.scalar(
            select(LoanApplication.branch_id).where(
                LoanApplication.org_id == org_id,
                LoanApplication.id == original.application_id,
            )
        )
    from dogeapi.operations import approval_service

    return await approval_service.request_approval(
        session,
        org_id=org_id,
        branch_id=branch_id,
        aggregate_type="journal_entry",
        aggregate_id=original.id,
        aggregate_reference=original.entry_no,
        action="reverse_journal",
        requested_by=actor_id,
        assigned_role="finance",
        reason=reason,
        payload={
            "journal_id": str(original.id),
            "entry_no": original.entry_no,
            "description": original.description,
            "reason": reason,
            "idempotency_key": idempotency_key,
        },
        priority="high",
        sla_hours=4,
    )


async def fund_cashbox(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    cashbox_id: UUID,
    amount: Decimal,
    external_reference: str,
    idempotency_key: str,
) -> CashTransaction:
    existing = await session.scalar(
        select(CashTransaction).where(
            CashTransaction.org_id == org_id, CashTransaction.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return existing
    cashbox = await session.scalar(select(Cashbox).where(Cashbox.org_id == org_id, Cashbox.id == cashbox_id))
    if cashbox is None:
        raise _not_found("Cashbox")
    accounts, _ = await ensure_finance_masters(session, org_id, cashbox.branch_id)
    journal = await post_journal(
        session,
        org_id,
        actor_id,
        None,
        "cash_funding",
        f"journal:{idempotency_key}",
        f"Cash funding {external_reference}",
        [
            (accounts["1100"], amount, Decimal("0"), "Cash funded"),
            (accounts["3100"], Decimal("0"), amount, "Funding source"),
        ],
    )
    cashbox.balance += amount
    transaction = CashTransaction(
        org_id=org_id,
        cashbox_id=cashbox.id,
        loan_account_id=None,
        journal_entry_id=journal.id,
        transaction_type="cash_funding",
        direction="in",
        amount=amount,
        idempotency_key=idempotency_key,
        external_reference=external_reference,
    )
    session.add(transaction)
    await session.flush()
    return transaction


async def post_disbursement(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    application: LoanApplication,
    account: LoanAccount,
    external_reference: str,
    idempotency_key: str,
) -> CashTransaction:
    existing = await session.scalar(
        select(CashTransaction).where(
            CashTransaction.org_id == org_id, CashTransaction.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return existing
    accounts, cashbox = await ensure_finance_masters(session, org_id, application.branch_id)
    if cashbox.balance < account.principal_amount:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cashbox balance is insufficient for disbursement")
    fee = account.total_due_amount - account.principal_amount
    journal = await post_journal(
        session,
        org_id,
        actor_id,
        application.id,
        "loan_disbursement",
        f"journal:{idempotency_key}",
        f"Pawn loan disbursement {account.account_no}",
        [
            (accounts["1200"], account.principal_amount, Decimal("0"), "Principal receivable"),
            (accounts["1210"], fee, Decimal("0"), "Service fee receivable"),
            (accounts["1100"], Decimal("0"), account.principal_amount, "Cash disbursed"),
            (accounts["4100"], Decimal("0"), fee, "Service fee income"),
        ],
    )
    cashbox.balance -= account.principal_amount
    account.outstanding_principal = account.principal_amount
    account.outstanding_fee = fee
    account.paid_amount = Decimal("0")
    session.add_all(
        [
            LoanLedgerEntry(
                org_id=org_id,
                loan_account_id=account.id,
                entry_type="principal_disbursement",
                debit_amount=account.principal_amount,
                credit_amount=Decimal("0"),
                balance_after=account.principal_amount,
                external_reference=external_reference,
                idempotency_key=f"{idempotency_key}:principal",
            ),
            LoanLedgerEntry(
                org_id=org_id,
                loan_account_id=account.id,
                entry_type="service_fee_charge",
                debit_amount=fee,
                credit_amount=Decimal("0"),
                balance_after=account.total_due_amount,
                external_reference=external_reference,
                idempotency_key=f"{idempotency_key}:fee",
            ),
        ]
    )
    transaction = CashTransaction(
        org_id=org_id,
        cashbox_id=cashbox.id,
        loan_account_id=account.id,
        journal_entry_id=journal.id,
        transaction_type="disbursement",
        direction="out",
        amount=account.principal_amount,
        idempotency_key=idempotency_key,
        external_reference=external_reference,
    )
    session.add(transaction)
    await session.flush()
    return transaction


async def post_repayment(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    application: LoanApplication,
    account: LoanAccount,
    amount: Decimal,
    external_reference: str,
    idempotency_key: str,
) -> CashTransaction:
    existing = await session.scalar(
        select(CashTransaction).where(
            CashTransaction.org_id == org_id, CashTransaction.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return existing
    accounts, cashbox = await ensure_finance_masters(session, org_id, application.branch_id)
    journal = await post_journal(
        session,
        org_id,
        actor_id,
        application.id,
        "loan_repayment",
        f"journal:{idempotency_key}",
        f"Pawn loan repayment {account.account_no}",
        [
            (accounts["1100"], amount, Decimal("0"), "Cash received"),
            (accounts["1200"], Decimal("0"), account.outstanding_principal, "Principal settled"),
            (accounts["1210"], Decimal("0"), account.outstanding_fee, "Fee settled"),
        ],
    )
    cashbox.balance += amount
    account.paid_amount += amount
    account.outstanding_principal = Decimal("0")
    account.outstanding_fee = Decimal("0")
    session.add(
        LoanLedgerEntry(
            org_id=org_id,
            loan_account_id=account.id,
            entry_type="repayment",
            debit_amount=Decimal("0"),
            credit_amount=amount,
            balance_after=Decimal("0"),
            external_reference=external_reference,
            idempotency_key=f"{idempotency_key}:repayment",
        )
    )
    collection_case = await session.scalar(
        select(CollectionCase).where(CollectionCase.org_id == org_id, CollectionCase.loan_account_id == account.id)
    )
    if collection_case is not None:
        collection_case.outstanding_amount = Decimal("0")
        collection_case.status = "closed"
        collection_case.aging_bucket = "settled"
    transaction = CashTransaction(
        org_id=org_id,
        cashbox_id=cashbox.id,
        loan_account_id=account.id,
        journal_entry_id=journal.id,
        transaction_type="repayment",
        direction="in",
        amount=amount,
        idempotency_key=idempotency_key,
        external_reference=external_reference,
    )
    session.add(transaction)
    await session.flush()
    return transaction


async def open_teller_session(session: AsyncSession, org_id: UUID, user_id: UUID, cashbox_id: UUID) -> TellerSession:
    cashbox = await session.scalar(select(Cashbox).where(Cashbox.org_id == org_id, Cashbox.id == cashbox_id))
    if cashbox is None:
        raise _not_found("Cashbox")
    existing = await session.scalar(
        select(TellerSession).where(
            TellerSession.org_id == org_id,
            TellerSession.teller_user_id == user_id,
            TellerSession.status == "open",
        )
    )
    if existing is not None:
        return existing
    item = TellerSession(
        org_id=org_id,
        cashbox_id=cashbox.id,
        teller_user_id=user_id,
        opening_balance=cashbox.balance,
    )
    session.add(item)
    await session.flush()
    return item


async def close_teller_session(
    session: AsyncSession, org_id: UUID, user_id: UUID, session_id: UUID, actual_balance: Decimal
) -> TellerSession:
    item = await session.scalar(
        select(TellerSession).where(TellerSession.org_id == org_id, TellerSession.id == session_id)
    )
    if item is None:
        raise _not_found("Teller session")
    if item.teller_user_id != user_id or item.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "Teller session cannot be closed by this user")
    cashbox = await session.scalar(select(Cashbox).where(Cashbox.org_id == org_id, Cashbox.id == item.cashbox_id))
    item.expected_closing_balance = cashbox.balance if cashbox else Decimal("0")
    item.actual_closing_balance = actual_balance
    item.status = "closed" if actual_balance == item.expected_closing_balance else "variance"
    item.closed_at = datetime.now(UTC)
    await session.flush()
    return item


async def finance_overview(session: AsyncSession, org_id: UUID) -> FinanceOverview:
    cash_balance = await session.scalar(
        select(func.coalesce(func.sum(Cashbox.balance), Decimal("0"))).where(Cashbox.org_id == org_id)
    )
    active_count = await session.scalar(
        select(func.count(LoanAccount.id)).where(LoanAccount.org_id == org_id, LoanAccount.status == "active")
    )
    outstanding = (
        await session.execute(
            select(
                func.coalesce(func.sum(LoanAccount.outstanding_principal), Decimal("0")),
                func.coalesce(func.sum(LoanAccount.outstanding_fee), Decimal("0")),
            ).where(LoanAccount.org_id == org_id)
        )
    ).one()
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    payments = await session.scalar(
        select(func.coalesce(func.sum(CashTransaction.amount), Decimal("0"))).where(
            CashTransaction.org_id == org_id,
            CashTransaction.transaction_type == "repayment",
            CashTransaction.occurred_at >= start,
        )
    )
    open_sessions = await session.scalar(
        select(func.count(TellerSession.id)).where(TellerSession.org_id == org_id, TellerSession.status == "open")
    )
    transactions = list(
        await session.scalars(
            select(CashTransaction)
            .where(CashTransaction.org_id == org_id)
            .order_by(CashTransaction.occurred_at.desc())
            .limit(12)
        )
    )
    return FinanceOverview(
        cash_balance=cash_balance or Decimal("0"),
        active_loan_count=int(active_count or 0),
        outstanding_principal=outstanding[0],
        outstanding_fee=outstanding[1],
        payment_today=payments or Decimal("0"),
        open_teller_sessions=int(open_sessions or 0),
        recent_transactions=[
            {
                "id": item.id,
                "type": item.transaction_type,
                "direction": item.direction,
                "amount": item.amount,
                "reference": item.external_reference,
                "occurred_at": item.occurred_at,
            }
            for item in transactions
        ],
    )


async def financial_reports(session: AsyncSession, org_id: UUID) -> FinancialReports:
    trial_rows = (
        await session.execute(
            select(
                GLAccount.code,
                GLAccount.name,
                GLAccount.account_type,
                func.coalesce(func.sum(JournalLine.debit_amount), Decimal("0")),
                func.coalesce(func.sum(JournalLine.credit_amount), Decimal("0")),
            )
            .join(JournalLine, JournalLine.account_id == GLAccount.id, isouter=True)
            .where(GLAccount.org_id == org_id, (JournalLine.org_id == org_id) | (JournalLine.org_id.is_(None)))
            .group_by(GLAccount.id)
            .order_by(GLAccount.code)
        )
    ).all()
    portfolio = (
        await session.execute(
            select(
                func.count(LoanAccount.id),
                func.coalesce(func.sum(LoanAccount.principal_amount), Decimal("0")),
                func.coalesce(func.sum(LoanAccount.outstanding_principal), Decimal("0")),
                func.coalesce(func.sum(LoanAccount.paid_amount), Decimal("0")),
            ).where(LoanAccount.org_id == org_id)
        )
    ).one()
    aging_rows = (
        await session.execute(
            select(
                CollectionCase.aging_bucket, func.count(CollectionCase.id), func.sum(CollectionCase.outstanding_amount)
            )
            .where(CollectionCase.org_id == org_id)
            .group_by(CollectionCase.aging_bucket)
        )
    ).all()
    branch_rows = (
        await session.execute(
            select(Branch.code, Branch.name, func.count(LoanApplication.id), func.sum(LoanApplication.requested_amount))
            .join(LoanApplication, LoanApplication.branch_id == Branch.id, isouter=True)
            .where(Branch.org_id == org_id, (LoanApplication.org_id == org_id) | (LoanApplication.org_id.is_(None)))
            .group_by(Branch.id)
            .order_by(Branch.code)
        )
    ).all()
    return FinancialReports(
        trial_balance=[
            {
                "code": code,
                "name": name,
                "account_type": account_type,
                "debit": debit,
                "credit": credit,
                "balance": debit - credit,
            }
            for code, name, account_type, debit, credit in trial_rows
        ],
        loan_portfolio={
            "loan_count": int(portfolio[0]),
            "principal": portfolio[1],
            "outstanding": portfolio[2],
            "paid": portfolio[3],
        },
        aging=[
            {"bucket": bucket, "count": int(count), "outstanding": amount or Decimal("0")}
            for bucket, count, amount in aging_rows
        ],
        branch_analytics=[
            {"branch_code": code, "branch_name": name, "applications": int(count), "requested_amount": amount or 0}
            for code, name, count, amount in branch_rows
        ],
    )


async def list_collections(session: AsyncSession, org_id: UUID) -> list[dict[str, object]]:
    rows = (
        await session.execute(
            select(CollectionCase, LoanAccount, LoanApplication)
            .join(LoanAccount, LoanAccount.id == CollectionCase.loan_account_id)
            .join(LoanApplication, LoanApplication.id == LoanAccount.application_id)
            .where(
                CollectionCase.org_id == org_id,
                LoanAccount.org_id == org_id,
                LoanApplication.org_id == org_id,
            )
            .order_by(CollectionCase.due_at)
        )
    ).all()
    now = datetime.now(UTC)
    output: list[dict[str, object]] = []
    for item, account, application in rows:
        days = (now - item.due_at).days
        bucket = "current" if days <= 0 else "1-30" if days <= 30 else "31-60" if days <= 60 else "60+"
        if item.status != "closed":
            item.aging_bucket = bucket
        output.append(
            {
                "id": item.id,
                "application_id": application.id,
                "application_no": application.application_no,
                "account_no": account.account_no,
                "due_at": item.due_at,
                "outstanding_amount": item.outstanding_amount,
                "aging_bucket": item.aging_bucket,
                "status": item.status,
                "assigned_user_id": item.assigned_user_id,
            }
        )
    return output


async def add_collection_note(
    session: AsyncSession, org_id: UUID, actor_id: UUID, case_id: UUID, data: CollectionNoteCreate
) -> CollectionNote:
    item = await session.scalar(
        select(CollectionCase).where(CollectionCase.org_id == org_id, CollectionCase.id == case_id)
    )
    if item is None:
        raise _not_found("Collection case")
    note = CollectionNote(
        org_id=org_id,
        collection_case_id=item.id,
        actor_user_id=actor_id,
        **data.model_dump(),
    )
    item.next_action_at = data.next_action_at
    item.status = "follow_up"
    session.add(note)
    await session.flush()
    return note


async def create_regulatory_template(
    session: AsyncSession, org_id: UUID, data: RegulatoryTemplateCreate
) -> RegulatoryReportTemplate:
    item = RegulatoryReportTemplate(org_id=org_id, status="draft", **data.model_dump())
    session.add(item)
    await session.flush()
    return item


async def create_regulatory_run(
    session: AsyncSession, org_id: UUID, actor_id: UUID, data: RegulatoryRunCreate
) -> RegulatoryReportRun:
    template = await session.scalar(
        select(RegulatoryReportTemplate).where(
            RegulatoryReportTemplate.org_id == org_id, RegulatoryReportTemplate.id == data.template_id
        )
    )
    if template is None:
        raise _not_found("Regulatory report template")
    if data.period_end < data.period_start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Report period is invalid")
    report = await financial_reports(session, org_id)
    validations: list[dict[str, object]] = []
    if template.status != "active":
        validations.append({"level": "warning", "code": "TEMPLATE_DRAFT", "message": "Template is not approved"})
    loan_rows = (
        await session.execute(
            select(LoanAccount, LoanApplication, Asset)
            .join(LoanApplication, LoanApplication.id == LoanAccount.application_id)
            .join(Asset, Asset.application_id == LoanApplication.id)
            .where(LoanAccount.org_id == org_id, LoanApplication.org_id == org_id, Asset.org_id == org_id)
            .order_by(LoanAccount.account_no)
        )
    ).all()
    payload = jsonable_encoder(
        {
            "report_type": template.report_type,
            "template_code": template.code,
            "template_version": template.version,
            "period_start": data.period_start.isoformat(),
            "period_end": data.period_end.isoformat(),
            "portfolio": report.loan_portfolio,
            "aging": report.aging,
            "trial_balance": report.trial_balance,
            "branch_analytics": report.branch_analytics,
            "form_2100": [
                {
                    "account_no": account.account_no,
                    "application_no": application.application_no,
                    "loan_status": account.status,
                    "asset_category": asset.category,
                    "principal_amount": account.principal_amount,
                    "outstanding_principal": account.outstanding_principal,
                    "outstanding_fee": account.outstanding_fee,
                    "due_at": account.due_at,
                }
                for account, application, asset in loan_rows
            ],
            "generated_at": datetime.now(UTC).isoformat(),
            "submission_status": "not_submitted",
        }
    )
    item = RegulatoryReportRun(
        org_id=org_id,
        template_id=template.id,
        period_start=data.period_start,
        period_end=data.period_end,
        status="validation_failed" if any(x["level"] == "error" for x in validations) else "draft",
        validation_results=validations,
        report_payload=payload,
        generated_by_user_id=actor_id,
    )
    session.add(item)
    await session.flush()
    return item


async def export_regulatory_package(session: AsyncSession, org_id: UUID, run_id: UUID) -> tuple[bytes, str, str]:
    run = await session.scalar(
        select(RegulatoryReportRun).where(RegulatoryReportRun.org_id == org_id, RegulatoryReportRun.id == run_id)
    )
    if run is None:
        raise _not_found("Regulatory report run")
    if run.status != "approved":
        raise HTTPException(status.HTTP_409_CONFLICT, "Report package can only be exported after sign-off")
    template = await session.scalar(
        select(RegulatoryReportTemplate).where(
            RegulatoryReportTemplate.org_id == org_id,
            RegulatoryReportTemplate.id == run.template_id,
        )
    )
    if template is None:
        raise _not_found("Regulatory report template")
    source_url = str(template.mapping_schema.get("source_url") or "")
    manifest = {
        "regulation": "SEOJK 17/SEOJK.06/2025",
        "source_url": source_url,
        "template_code": template.code,
        "template_version": template.version,
        "period_start": run.period_start.isoformat(),
        "period_end": run.period_end.isoformat(),
        "revision": run.revision,
        "approval_id": str(run.approved_by_user_id),
        "approved_at": run.approved_at.isoformat() if run.approved_at else None,
        "submission_status": "not_submitted",
        "notice": "Package kerja terversi; unggah hanya setelah validasi terhadap kanal dan kamus data OJK tenant.",
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        _write_csv(archive, "1100_laporan_posisi_keuangan.csv", run.report_payload.get("trial_balance", []))
        _write_csv(archive, "2100_rincian_penyaluran_pinjaman.csv", run.report_payload.get("form_2100", []))
        _write_csv(archive, "9100_analisis_kesesuaian_aset_liabilitas.csv", run.report_payload.get("aging", []))
        _write_csv(archive, "branch_reconciliation.csv", run.report_payload.get("branch_analytics", []))
    content = output.getvalue()
    checksum = hashlib.sha256(content).hexdigest()
    filename = f"OJK-{template.code}-{run.period_end.isoformat()}-R{run.revision}.zip"
    return content, filename, checksum


def _write_csv(archive: zipfile.ZipFile, name: str, rows: object) -> None:
    normalized = rows if isinstance(rows, list) else []
    buffer = io.StringIO(newline="")
    if normalized and isinstance(normalized[0], dict):
        fieldnames = list(normalized[0].keys())
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(normalized)
    archive.writestr(name, buffer.getvalue().encode("utf-8-sig"))


async def submit_regulatory_run_for_approval(
    session: AsyncSession, org_id: UUID, actor_id: UUID, run_id: UUID, reason: str
) -> ApprovalRequest:
    report = await session.scalar(
        select(RegulatoryReportRun)
        .where(RegulatoryReportRun.org_id == org_id, RegulatoryReportRun.id == run_id)
        .with_for_update()
    )
    if report is None:
        raise _not_found("Regulatory report run")
    if report.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a valid draft can be submitted for sign-off")
    if any(result.get("level") == "error" for result in report.validation_results):
        raise HTTPException(status.HTTP_409_CONFLICT, "Validation errors must be resolved before sign-off")
    template = await session.scalar(
        select(RegulatoryReportTemplate).where(
            RegulatoryReportTemplate.org_id == org_id,
            RegulatoryReportTemplate.id == report.template_id,
        )
    )
    if template is None:
        raise _not_found("Regulatory report template")
    report.status = "pending_approval"
    from dogeapi.operations import approval_service

    return await approval_service.request_approval(
        session,
        org_id=org_id,
        branch_id=None,
        aggregate_type="regulatory_report",
        aggregate_id=report.id,
        aggregate_reference=f"{template.code}/{report.period_end.isoformat()}/R{report.revision}",
        action="sign_off_regulatory_report",
        requested_by=actor_id,
        assigned_role="auditor",
        reason=reason,
        payload={
            "template_code": template.code,
            "template_version": template.version,
            "report_type": template.report_type,
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "revision": report.revision,
            "validation_results": report.validation_results,
        },
        priority="high",
        sla_hours=8,
    )


async def create_inventory_check(
    session: AsyncSession, org_id: UUID, actor_id: UUID, location_id: UUID
) -> InventoryCheck:
    location = await session.scalar(
        select(CustodyLocation).where(CustodyLocation.org_id == org_id, CustodyLocation.id == location_id)
    )
    if location is None:
        raise _not_found("Custody location")
    item = InventoryCheck(org_id=org_id, location_id=location_id, performed_by_user_id=actor_id)
    session.add(item)
    await session.flush()
    return item


async def inventory_check_detail(session: AsyncSession, org_id: UUID, check_id: UUID) -> dict[str, object]:
    item = await session.scalar(
        select(InventoryCheck).where(InventoryCheck.org_id == org_id, InventoryCheck.id == check_id)
    )
    if item is None:
        raise _not_found("Inventory check")
    location = await session.scalar(
        select(CustodyLocation).where(
            CustodyLocation.org_id == org_id,
            CustodyLocation.id == item.location_id,
        )
    )
    observations = {
        row.application_id: row
        for row in await session.scalars(
            select(InventoryCheckItem).where(
                InventoryCheckItem.org_id == org_id,
                InventoryCheckItem.inventory_check_id == item.id,
            )
        )
    }
    candidates = (
        await session.execute(
            select(Asset, LoanApplication)
            .join(
                LoanApplication,
                (LoanApplication.id == Asset.application_id) & (LoanApplication.org_id == org_id),
            )
            .where(
                Asset.org_id == org_id,
                Asset.collateral_status.in_({"stored", "incident_hold", "release_authorized"}),
            )
            .order_by(LoanApplication.application_no)
        )
    ).all()
    assets: list[dict[str, object]] = []
    for asset, application in candidates:
        last_location = await session.scalar(
            select(CustodyEvent.location_id)
            .where(CustodyEvent.org_id == org_id, CustodyEvent.application_id == application.id)
            .order_by(CustodyEvent.occurred_at.desc())
            .limit(1)
        )
        if last_location != item.location_id:
            continue
        observation = observations.get(application.id)
        assets.append(
            {
                "application_id": application.id,
                "application_no": application.application_no,
                "asset_code": asset.asset_code,
                "asset_label": " ".join(value for value in (asset.brand, asset.model) if value) or asset.category,
                "expected_status": asset.collateral_status,
                "observed_status": observation.observed_status if observation else None,
                "result": observation.result if observation else None,
                "note": observation.note if observation else None,
            }
        )
    return {
        "id": item.id,
        "location": {
            "id": item.location_id,
            "code": location.code if location else "",
            "name": location.name if location else "",
        },
        "status": item.status,
        "performed_by_user_id": item.performed_by_user_id,
        "reviewed_by_user_id": item.reviewed_by_user_id,
        "counted_at": item.counted_at,
        "approved_at": item.approved_at,
        "assets": assets,
    }


async def submit_inventory_check(
    session: AsyncSession, org_id: UUID, actor_id: UUID, check_id: UUID, data: InventoryCheckSubmit
) -> InventoryCheck:
    item = await session.scalar(
        select(InventoryCheck).where(InventoryCheck.org_id == org_id, InventoryCheck.id == check_id)
    )
    if item is None:
        raise _not_found("Inventory check")
    if item.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "Inventory check is not editable")
    for observation in data.observations:
        asset = await session.scalar(
            select(Asset).where(Asset.org_id == org_id, Asset.application_id == observation.application_id)
        )
        if asset is None:
            raise _not_found("Collateral asset")
        session.add(
            InventoryCheckItem(
                org_id=org_id,
                inventory_check_id=item.id,
                application_id=observation.application_id,
                expected_status=asset.collateral_status,
                observed_status=observation.observed_status,
                result="matched" if asset.collateral_status == observation.observed_status else "variance",
                note=observation.note,
            )
        )
    item.status = "submitted"
    await session.flush()
    location = await session.scalar(
        select(CustodyLocation).where(
            CustodyLocation.org_id == org_id,
            CustodyLocation.id == item.location_id,
        )
    )
    if location is None:
        raise _not_found("Custody location")
    variance_count = int(
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
    )
    from dogeapi.operations import approval_service

    await approval_service.request_approval(
        session,
        org_id=org_id,
        branch_id=location.branch_id,
        aggregate_type="inventory_check",
        aggregate_id=item.id,
        aggregate_reference=f"STOCK-{str(item.id)[:8].upper()}",
        action="approve_inventory_check",
        requested_by=actor_id,
        assigned_role="branch_manager",
        reason="Hasil stock opname menunggu review independen",
        payload={
            "location_id": str(item.location_id),
            "observation_count": len(data.observations),
            "variance_count": variance_count,
        },
        priority="high" if variance_count else "normal",
        sla_hours=4,
    )
    return item


async def approve_inventory_check(
    session: AsyncSession, org_id: UUID, reviewer_id: UUID, check_id: UUID
) -> InventoryCheck:
    item = await session.scalar(
        select(InventoryCheck).where(InventoryCheck.org_id == org_id, InventoryCheck.id == check_id)
    )
    if item is None:
        raise _not_found("Inventory check")
    if item.status != "submitted":
        raise HTTPException(status.HTTP_409_CONFLICT, "Inventory check must be submitted first")
    if item.performed_by_user_id == reviewer_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Maker and reviewer must be different users")
    item.reviewed_by_user_id = reviewer_id
    item.approved_at = datetime.now(UTC)
    item.status = "approved"
    await session.flush()
    return item
