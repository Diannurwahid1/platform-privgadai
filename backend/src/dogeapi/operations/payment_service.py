"""Payment allocation, controlled adjustments, and finance reconciliation."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    Asset,
    Borrower,
    Branch,
    Cashbox,
    CashTransaction,
    CollectionCase,
    CustodyEvent,
    GLAccount,
    JournalEntry,
    JournalLine,
    LoanAccount,
    LoanApplication,
    LoanLedgerEntry,
    PaymentAdjustment,
    PaymentReceipt,
    ReconciliationRun,
    TellerSession,
)
from dogeapi.operations import erp_service, mvp_service
from dogeapi.operations.payment_schemas import PaymentAdjustmentCreate, PaymentCreate, ReconciliationCreate

FINANCE_ROLES = {"ops_admin", "branch_manager", "finance", "teller"}


async def _loan_context(
    session: AsyncSession, org_id: UUID, loan_id: UUID, *, lock: bool = False
) -> tuple[LoanAccount, LoanApplication]:
    statement = (
        select(LoanAccount, LoanApplication)
        .join(LoanApplication, (LoanApplication.org_id == org_id) & (LoanApplication.id == LoanAccount.application_id))
        .where(LoanAccount.org_id == org_id, LoanAccount.id == loan_id)
    )
    if lock:
        statement = statement.with_for_update()
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Loan account tidak ditemukan")
    return row


async def record_payment(session: AsyncSession, org_id: UUID, actor_id: UUID, data: PaymentCreate) -> PaymentReceipt:
    existing = await session.scalar(
        select(PaymentReceipt).where(
            PaymentReceipt.org_id == org_id, PaymentReceipt.idempotency_key == data.idempotency_key
        )
    )
    if existing is not None:
        return existing
    account, application = await _loan_context(session, org_id, data.loan_account_id, lock=True)
    await mvp_service.ensure_operational_access(session, org_id, actor_id, application.branch_id, FINANCE_ROLES)
    if account.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Pembayaran hanya dapat diposting pada pinjaman aktif")
    total_outstanding = account.outstanding_fee + account.outstanding_principal
    if data.amount > total_outstanding:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Pembayaran melebihi saldo terutang")
    accounts, cashbox = await erp_service.ensure_finance_masters(session, org_id, application.branch_id)
    teller: TellerSession | None = None
    if data.channel == "cash":
        teller = await session.scalar(
            select(TellerSession).where(
                TellerSession.org_id == org_id,
                TellerSession.cashbox_id == cashbox.id,
                TellerSession.teller_user_id == actor_id,
                TellerSession.status == "open",
            )
        )
        if teller is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Pembayaran tunai memerlukan sesi teller aktif milik petugas")
    allocated_fee = min(data.amount, account.outstanding_fee)
    allocated_principal = data.amount - allocated_fee
    lines = [(accounts["1100"], data.amount, Decimal("0"), f"Receipt {data.external_reference}")]
    if allocated_fee:
        lines.append((accounts["1210"], Decimal("0"), allocated_fee, "Fee allocation"))
    if allocated_principal:
        lines.append((accounts["1200"], Decimal("0"), allocated_principal, "Principal allocation"))
    journal = await erp_service.post_journal(
        session,
        org_id,
        actor_id,
        application.id,
        "loan_payment",
        f"journal:{data.idempotency_key}",
        f"Payment allocation for {account.account_no}",
        lines,
    )
    account.outstanding_fee -= allocated_fee
    account.outstanding_principal -= allocated_principal
    account.paid_amount += data.amount
    cashbox.balance += data.amount
    balance_after = account.outstanding_fee + account.outstanding_principal
    ledger_entries: list[LoanLedgerEntry] = []
    if allocated_fee:
        ledger_entries.append(
            LoanLedgerEntry(
                org_id=org_id,
                loan_account_id=account.id,
                entry_type="payment_fee",
                debit_amount=0,
                credit_amount=allocated_fee,
                balance_after=account.outstanding_principal + account.outstanding_fee + allocated_principal,
                external_reference=data.external_reference,
                idempotency_key=f"{data.idempotency_key}:fee",
            )
        )
    if allocated_principal:
        ledger_entries.append(
            LoanLedgerEntry(
                org_id=org_id,
                loan_account_id=account.id,
                entry_type="payment_principal",
                debit_amount=0,
                credit_amount=allocated_principal,
                balance_after=balance_after,
                external_reference=data.external_reference,
                idempotency_key=f"{data.idempotency_key}:principal",
            )
        )
    transaction = CashTransaction(
        org_id=org_id,
        cashbox_id=cashbox.id,
        teller_session_id=teller.id if teller else None,
        loan_account_id=account.id,
        journal_entry_id=journal.id,
        transaction_type="payment",
        direction="in",
        amount=data.amount,
        idempotency_key=data.idempotency_key,
        external_reference=data.external_reference,
    )
    receipt = PaymentReceipt(
        org_id=org_id,
        loan_account_id=account.id,
        cashbox_id=cashbox.id,
        teller_session_id=teller.id if teller else None,
        journal_entry_id=journal.id,
        receipt_no=f"RCPT-{datetime.now(UTC).strftime('%y%m%d')}-{secrets.token_hex(4).upper()}",
        channel=data.channel,
        amount=data.amount,
        allocated_fee=allocated_fee,
        allocated_principal=allocated_principal,
        external_reference=data.external_reference,
        idempotency_key=data.idempotency_key,
        received_by_user_id=actor_id,
    )
    session.add_all([*ledger_entries, transaction, receipt])
    if balance_after == 0:
        account.status = "settled"
        account.settled_at = datetime.now(UTC)
        collection = await session.scalar(
            select(CollectionCase).where(CollectionCase.org_id == org_id, CollectionCase.loan_account_id == account.id)
        )
        if collection is not None:
            collection.outstanding_amount = 0
            collection.status = "closed"
            collection.aging_bucket = "settled"
        await session.flush()
        await _request_release_if_stored(session, org_id, actor_id, account, application, receipt)
    await session.flush()
    return receipt


async def _request_release_if_stored(
    session: AsyncSession,
    org_id: UUID,
    actor_id: UUID,
    account: LoanAccount,
    application: LoanApplication,
    receipt: PaymentReceipt,
) -> None:
    asset = await session.scalar(select(Asset).where(Asset.org_id == org_id, Asset.application_id == application.id))
    if asset is None or asset.collateral_status != "stored":
        return
    latest = await session.scalar(
        select(CustodyEvent)
        .where(CustodyEvent.org_id == org_id, CustodyEvent.application_id == application.id)
        .order_by(CustodyEvent.occurred_at.desc())
        .limit(1)
    )
    if latest is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Lokasi custody aktif tidak ditemukan")
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
        reason="Saldo pinjaman lunas; agunan menunggu otorisasi pelepasan",
        payload={
            "application_id": str(application.id),
            "loan_account_id": str(account.id),
            "payment_receipt_id": str(receipt.id),
            "location_id": str(latest.location_id),
            "condition_note": "Release approved after allocated payment",
            "settlement_reference": receipt.receipt_no,
            "settlement_amount": str(receipt.amount),
        },
        priority="high",
        sla_hours=4,
    )


async def request_adjustment(
    session: AsyncSession, org_id: UUID, actor_id: UUID, data: PaymentAdjustmentCreate
) -> PaymentAdjustment:
    existing = await session.scalar(
        select(PaymentAdjustment).where(
            PaymentAdjustment.org_id == org_id, PaymentAdjustment.idempotency_key == data.idempotency_key
        )
    )
    if existing is not None:
        return existing
    account, application = await _loan_context(session, org_id, data.loan_account_id, lock=True)
    await mvp_service.ensure_operational_access(session, org_id, actor_id, application.branch_id, FINANCE_ROLES)
    receipt: PaymentReceipt | None = None
    if data.payment_receipt_id:
        receipt = await session.scalar(
            select(PaymentReceipt).where(PaymentReceipt.org_id == org_id, PaymentReceipt.id == data.payment_receipt_id)
        )
        if receipt is None or receipt.loan_account_id != account.id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Receipt tidak sesuai loan account")
        refunded = (
            await session.scalar(
                select(func.coalesce(func.sum(PaymentAdjustment.amount), 0)).where(
                    PaymentAdjustment.org_id == org_id,
                    PaymentAdjustment.payment_receipt_id == receipt.id,
                    PaymentAdjustment.adjustment_type.in_({"refund", "payment_reversal"}),
                    PaymentAdjustment.status.in_({"pending_approval", "posted"}),
                )
            )
        ) or Decimal("0")
        if data.amount + refunded > receipt.amount:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Refund/reversal melebihi nilai receipt tersisa")
    if data.adjustment_type in {"waiver", "credit_adjustment"}:
        outstanding = account.outstanding_principal if data.component == "principal" else account.outstanding_fee
        if data.amount > outstanding:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Adjustment melebihi saldo komponen")
    item = PaymentAdjustment(org_id=org_id, requested_by_user_id=actor_id, **data.model_dump())
    session.add(item)
    await session.flush()
    from dogeapi.operations import approval_service

    await approval_service.request_approval(
        session,
        org_id=org_id,
        branch_id=application.branch_id,
        aggregate_type="payment_adjustment",
        aggregate_id=item.id,
        aggregate_reference=f"ADJ-{account.account_no}-{item.id.hex[:8].upper()}",
        action="post_payment_adjustment",
        requested_by=actor_id,
        assigned_role="branch_manager",
        reason=data.reason,
        payload={
            "loan_account_id": str(account.id),
            "account_no": account.account_no,
            "receipt_no": receipt.receipt_no if receipt else None,
            "adjustment_type": data.adjustment_type,
            "component": data.component,
            "amount": str(data.amount),
            "external_reference": data.external_reference,
            "idempotency_key": data.idempotency_key,
        },
        priority="high",
        sla_hours=4,
    )
    return item


async def decide_adjustment(session: AsyncSession, item: PaymentAdjustment, actor_id: UUID, decision: str) -> None:
    if item.status != "pending_approval":
        raise HTTPException(status.HTTP_409_CONFLICT, "Adjustment tidak siap diputuskan")
    if decision != "approved":
        item.status = "rejected"
        return
    account, application = await _loan_context(session, item.org_id, item.loan_account_id, lock=True)
    accounts, cashbox = await erp_service.ensure_finance_masters(session, item.org_id, application.branch_id)
    if "5100" not in accounts:
        expense = GLAccount(
            org_id=item.org_id,
            code="5100",
            name="Beban Waiver dan Adjustment",
            account_type="expense",
            normal_balance="debit",
        )
        session.add(expense)
        await session.flush()
        accounts["5100"] = expense
    if "4200" not in accounts:
        income = GLAccount(
            org_id=item.org_id,
            code="4200",
            name="Pendapatan Adjustment",
            account_type="income",
            normal_balance="credit",
        )
        session.add(income)
        await session.flush()
        accounts["4200"] = income
    lines: list[tuple[GLAccount, Decimal, Decimal, str]]
    entry_type = item.adjustment_type
    if item.adjustment_type in {"waiver", "credit_adjustment"}:
        outstanding = account.outstanding_principal if item.component == "principal" else account.outstanding_fee
        if item.amount > outstanding:
            raise HTTPException(status.HTTP_409_CONFLICT, "Saldo komponen berubah dan tidak lagi mencukupi")
        receivable = accounts["1200" if item.component == "principal" else "1210"]
        lines = [
            (accounts["5100"], item.amount, 0, "Approved waiver/credit"),
            (receivable, 0, item.amount, "Receivable reduced"),
        ]
        if item.component == "principal":
            account.outstanding_principal -= item.amount
        else:
            account.outstanding_fee -= item.amount
        item.allocated_principal = item.amount if item.component == "principal" else 0
        item.allocated_fee = item.amount if item.component == "fee" else 0
    elif item.adjustment_type == "debit_adjustment":
        receivable = accounts["1200" if item.component == "principal" else "1210"]
        lines = [
            (receivable, item.amount, 0, "Approved debit adjustment"),
            (accounts["4200"], 0, item.amount, "Adjustment income"),
        ]
        if item.component == "principal":
            account.outstanding_principal += item.amount
        else:
            account.outstanding_fee += item.amount
        item.allocated_principal = item.amount if item.component == "principal" else 0
        item.allocated_fee = item.amount if item.component == "fee" else 0
        account.status = "active"
        account.settled_at = None
    else:
        receipt = await session.scalar(
            select(PaymentReceipt)
            .where(PaymentReceipt.org_id == item.org_id, PaymentReceipt.id == item.payment_receipt_id)
            .with_for_update()
        )
        if receipt is None or cashbox.balance < item.amount:
            raise HTTPException(status.HTTP_409_CONFLICT, "Receipt tidak tersedia atau saldo cashbox tidak mencukupi")
        already_principal = (
            await session.scalar(
                select(func.coalesce(func.sum(PaymentAdjustment.allocated_principal), 0)).where(
                    PaymentAdjustment.org_id == item.org_id,
                    PaymentAdjustment.payment_receipt_id == receipt.id,
                    PaymentAdjustment.status == "posted",
                )
            )
        ) or Decimal("0")
        already_fee = (
            await session.scalar(
                select(func.coalesce(func.sum(PaymentAdjustment.allocated_fee), 0)).where(
                    PaymentAdjustment.org_id == item.org_id,
                    PaymentAdjustment.payment_receipt_id == receipt.id,
                    PaymentAdjustment.status == "posted",
                )
            )
        ) or Decimal("0")
        principal = min(item.amount, receipt.allocated_principal - already_principal)
        fee = item.amount - principal
        if fee > receipt.allocated_fee - already_fee:
            raise HTTPException(status.HTTP_409_CONFLICT, "Nilai receipt tersisa tidak mencukupi")
        lines = [(accounts["1100"], 0, item.amount, "Cash refund")]
        if principal:
            lines.append((accounts["1200"], principal, 0, "Principal reinstated"))
        if fee:
            lines.append((accounts["1210"], fee, 0, "Fee reinstated"))
        account.outstanding_principal += principal
        account.outstanding_fee += fee
        account.paid_amount -= item.amount
        account.status = "active"
        account.settled_at = None
        cashbox.balance -= item.amount
        item.allocated_principal = principal
        item.allocated_fee = fee
        await session.flush()
    journal = await erp_service.post_journal(
        session,
        item.org_id,
        actor_id,
        application.id,
        entry_type,
        f"journal:adjustment:{item.idempotency_key}",
        f"{entry_type} {account.account_no}: {item.reason}",
        lines,
    )
    item.journal_entry_id = journal.id
    item.approved_by_user_id = actor_id
    item.posted_at = datetime.now(UTC)
    item.status = "posted"
    if item.adjustment_type in {"refund", "payment_reversal"}:
        transaction = CashTransaction(
            org_id=item.org_id,
            cashbox_id=cashbox.id,
            loan_account_id=account.id,
            journal_entry_id=journal.id,
            transaction_type=item.adjustment_type,
            direction="out",
            amount=item.amount,
            idempotency_key=f"cash:{item.idempotency_key}",
            external_reference=item.external_reference,
        )
        session.add(transaction)
        await session.flush()
        item.cash_transaction_id = transaction.id
        receipt = await session.scalar(select(PaymentReceipt).where(PaymentReceipt.id == item.payment_receipt_id))
        if receipt and item.amount == receipt.amount:
            receipt.status = "reversed" if item.adjustment_type == "payment_reversal" else "refunded"
    balance_after = account.outstanding_principal + account.outstanding_fee
    session.add(
        LoanLedgerEntry(
            org_id=item.org_id,
            loan_account_id=account.id,
            entry_type=entry_type,
            debit_amount=item.amount
            if item.adjustment_type in {"refund", "payment_reversal", "debit_adjustment"}
            else 0,
            credit_amount=item.amount if item.adjustment_type in {"waiver", "credit_adjustment"} else 0,
            balance_after=balance_after,
            external_reference=item.external_reference,
            idempotency_key=f"ledger:{item.idempotency_key}",
        )
    )
    collection = await session.scalar(
        select(CollectionCase).where(CollectionCase.org_id == item.org_id, CollectionCase.loan_account_id == account.id)
    )
    if collection is not None:
        collection.outstanding_amount = balance_after
        collection.status = "closed" if balance_after == 0 else "monitoring"
    if balance_after == 0:
        account.status = "settled"
        account.settled_at = datetime.now(UTC)
    await session.flush()


async def list_receipts(session: AsyncSession, org_id: UUID) -> list[dict[str, object]]:
    rows = (
        await session.execute(
            select(PaymentReceipt, LoanAccount, LoanApplication)
            .join(LoanAccount, (LoanAccount.org_id == org_id) & (LoanAccount.id == PaymentReceipt.loan_account_id))
            .join(
                LoanApplication, (LoanApplication.org_id == org_id) & (LoanApplication.id == LoanAccount.application_id)
            )
            .where(PaymentReceipt.org_id == org_id)
            .order_by(PaymentReceipt.occurred_at.desc())
            .limit(300)
        )
    ).all()
    return [
        {
            **_receipt(item),
            "account_no": account.account_no,
            "application_id": application.id,
            "application_no": application.application_no,
        }
        for item, account, application in rows
    ]


async def list_payment_accounts(session: AsyncSession, org_id: UUID) -> list[dict[str, object]]:
    rows = (
        await session.execute(
            select(LoanAccount, LoanApplication, Borrower, Branch)
            .join(
                LoanApplication, (LoanApplication.org_id == org_id) & (LoanApplication.id == LoanAccount.application_id)
            )
            .join(Borrower, (Borrower.org_id == org_id) & (Borrower.id == LoanApplication.borrower_id))
            .join(Branch, (Branch.org_id == org_id) & (Branch.id == LoanApplication.branch_id))
            .where(LoanAccount.org_id == org_id, LoanAccount.status.in_({"active", "settled"}))
            .order_by(LoanAccount.created_at.desc())
        )
    ).all()
    return [
        {
            "id": account.id,
            "account_no": account.account_no,
            "application_id": application.id,
            "application_no": application.application_no,
            "borrower_name": borrower.full_name,
            "branch_id": branch.id,
            "branch_code": branch.code,
            "status": account.status,
            "outstanding_principal": account.outstanding_principal,
            "outstanding_fee": account.outstanding_fee,
            "total_outstanding": account.outstanding_principal + account.outstanding_fee,
            "paid_amount": account.paid_amount,
            "due_at": account.due_at,
        }
        for account, application, borrower, branch in rows
    ]


async def list_adjustments(session: AsyncSession, org_id: UUID) -> list[dict[str, object]]:
    rows = list(
        await session.scalars(
            select(PaymentAdjustment)
            .where(PaymentAdjustment.org_id == org_id)
            .order_by(PaymentAdjustment.created_at.desc())
            .limit(300)
        )
    )
    return [
        {
            "id": row.id,
            "loan_account_id": row.loan_account_id,
            "payment_receipt_id": row.payment_receipt_id,
            "adjustment_type": row.adjustment_type,
            "component": row.component,
            "amount": row.amount,
            "allocated_fee": row.allocated_fee,
            "allocated_principal": row.allocated_principal,
            "status": row.status,
            "reason": row.reason,
            "external_reference": row.external_reference,
            "requested_by_user_id": row.requested_by_user_id,
            "approved_by_user_id": row.approved_by_user_id,
            "posted_at": row.posted_at,
            "created_at": row.created_at,
        }
        for row in rows
    ]


def _receipt(item: PaymentReceipt) -> dict[str, object]:
    return {
        "id": item.id,
        "loan_account_id": item.loan_account_id,
        "receipt_no": item.receipt_no,
        "channel": item.channel,
        "amount": item.amount,
        "allocated_fee": item.allocated_fee,
        "allocated_principal": item.allocated_principal,
        "status": item.status,
        "external_reference": item.external_reference,
        "received_by_user_id": item.received_by_user_id,
        "occurred_at": item.occurred_at,
    }


async def create_reconciliation(
    session: AsyncSession, org_id: UUID, actor_id: UUID, data: ReconciliationCreate
) -> ReconciliationRun:
    await mvp_service.ensure_any_operational_role(
        session, org_id, actor_id, {"ops_admin", "branch_manager", "finance", "auditor"}
    )
    start = datetime.combine(data.business_date, datetime.min.time(), tzinfo=UTC)
    end = start + timedelta(days=1)
    snapshot: dict[str, object]
    if data.scope == "cash_gl":
        filters = [
            CashTransaction.org_id == org_id,
            CashTransaction.occurred_at >= start,
            CashTransaction.occurred_at < end,
        ]
        if data.branch_id:
            filters.append(Cashbox.branch_id == data.branch_id)
        expected = (
            await session.scalar(
                select(
                    func.coalesce(
                        func.sum(
                            case(
                                (CashTransaction.direction == "in", CashTransaction.amount),
                                else_=-CashTransaction.amount,
                            )
                        ),
                        0,
                    )
                )
                .join(Cashbox, Cashbox.id == CashTransaction.cashbox_id)
                .where(*filters)
            )
        ) or Decimal("0")
        gl_filters = [
            CashTransaction.org_id == org_id,
            CashTransaction.occurred_at >= start,
            CashTransaction.occurred_at < end,
            GLAccount.code == "1100",
        ]
        if data.branch_id:
            gl_filters.append(Cashbox.branch_id == data.branch_id)
        observed = (
            await session.scalar(
                select(func.coalesce(func.sum(JournalLine.debit_amount - JournalLine.credit_amount), 0))
                .join(GLAccount, GLAccount.id == JournalLine.account_id)
                .join(CashTransaction, CashTransaction.journal_entry_id == JournalLine.journal_entry_id)
                .join(Cashbox, Cashbox.id == CashTransaction.cashbox_id)
                .where(*gl_filters)
            )
        ) or Decimal("0")
        snapshot = {"cash_transaction_net": str(expected), "cash_gl_net": str(observed)}
    elif data.scope == "loan_subledger_gl":
        loan_filters = [LoanAccount.org_id == org_id]
        if data.branch_id:
            loan_filters.append(LoanApplication.branch_id == data.branch_id)
        expected = (
            await session.scalar(
                select(func.coalesce(func.sum(LoanAccount.outstanding_principal + LoanAccount.outstanding_fee), 0))
                .join(LoanApplication, LoanApplication.id == LoanAccount.application_id)
                .where(*loan_filters)
            )
        ) or Decimal("0")
        journal_filters = [JournalEntry.org_id == org_id, GLAccount.code.in_({"1200", "1210"})]
        if data.branch_id:
            journal_filters.append(LoanApplication.branch_id == data.branch_id)
        observed = (
            await session.scalar(
                select(func.coalesce(func.sum(JournalLine.debit_amount - JournalLine.credit_amount), 0))
                .join(GLAccount, GLAccount.id == JournalLine.account_id)
                .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
                .join(LoanApplication, LoanApplication.id == JournalEntry.application_id)
                .where(*journal_filters)
            )
        ) or Decimal("0")
        snapshot = {"loan_subledger_outstanding": str(expected), "receivable_gl_balance": str(observed)}
    else:
        expected = (
            await session.scalar(
                select(func.coalesce(func.sum(PaymentReceipt.amount), 0))
                .join(LoanAccount, LoanAccount.id == PaymentReceipt.loan_account_id)
                .join(LoanApplication, LoanApplication.id == LoanAccount.application_id)
                .where(
                    PaymentReceipt.org_id == org_id,
                    PaymentReceipt.channel.in_({"bank_transfer", "virtual_account", "debit_card"}),
                    PaymentReceipt.occurred_at >= start,
                    PaymentReceipt.occurred_at < end,
                    *([LoanApplication.branch_id == data.branch_id] if data.branch_id else []),
                )
            )
        ) or Decimal("0")
        observed = data.observed_amount or Decimal("0")
        snapshot = {
            "system_bank_receipts": str(expected),
            "statement_total": str(observed),
            "statement_reference": data.statement_reference,
        }
    variance = observed - expected
    item = ReconciliationRun(
        org_id=org_id,
        branch_id=data.branch_id,
        scope=data.scope,
        business_date=data.business_date,
        status="matched" if abs(variance) <= data.tolerance_amount else "exception",
        expected_amount=expected,
        observed_amount=observed,
        variance_amount=variance,
        tolerance_amount=data.tolerance_amount,
        exception_count=0 if abs(variance) <= data.tolerance_amount else 1,
        snapshot=snapshot,
        created_by_user_id=actor_id,
    )
    session.add(item)
    await session.flush()
    return item


async def list_reconciliations(session: AsyncSession, org_id: UUID) -> list[dict[str, object]]:
    rows = list(
        await session.scalars(
            select(ReconciliationRun)
            .where(ReconciliationRun.org_id == org_id)
            .order_by(ReconciliationRun.created_at.desc())
            .limit(300)
        )
    )
    return [
        {
            "id": row.id,
            "branch_id": row.branch_id,
            "scope": row.scope,
            "business_date": row.business_date,
            "status": row.status,
            "expected_amount": row.expected_amount,
            "observed_amount": row.observed_amount,
            "variance_amount": row.variance_amount,
            "tolerance_amount": row.tolerance_amount,
            "exception_count": row.exception_count,
            "snapshot": row.snapshot,
            "resolution_note": row.resolution_note,
            "resolved_by_user_id": row.resolved_by_user_id,
            "resolved_at": row.resolved_at,
            "created_at": row.created_at,
        }
        for row in rows
    ]


async def request_reconciliation_resolution(
    session: AsyncSession, org_id: UUID, actor_id: UUID, run_id: UUID, note: str
) -> ReconciliationRun:
    item = await session.scalar(
        select(ReconciliationRun)
        .where(ReconciliationRun.org_id == org_id, ReconciliationRun.id == run_id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reconciliation run tidak ditemukan")
    if item.status != "exception":
        raise HTTPException(status.HTTP_409_CONFLICT, "Hanya exception yang dapat diselesaikan")
    item.status = "pending_resolution"
    item.resolution_note = note
    from dogeapi.operations import approval_service

    await approval_service.request_approval(
        session,
        org_id=org_id,
        branch_id=item.branch_id,
        aggregate_type="reconciliation",
        aggregate_id=item.id,
        aggregate_reference=f"REC-{item.scope}-{item.business_date}",
        action="resolve_reconciliation_exception",
        requested_by=actor_id,
        assigned_role="finance",
        reason=note,
        payload={
            "scope": item.scope,
            "business_date": item.business_date.isoformat(),
            "expected_amount": str(item.expected_amount),
            "observed_amount": str(item.observed_amount),
            "variance_amount": str(item.variance_amount),
            "snapshot": item.snapshot,
        },
        priority="high",
        sla_hours=4,
    )
    await session.flush()
    return item
