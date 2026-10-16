from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dogeapi.models import (
    ApprovalRequest,
    Borrower,
    Branch,
    Cashbox,
    ConfigurationVersion,
    JournalEntry,
    JournalLine,
    LoanAccount,
    LoanApplication,
    Membership,
    Organization,
    Role,
    User,
)
from dogeapi.operations import approval_service, payment_service
from dogeapi.operations.payment_schemas import PaymentAdjustmentCreate, PaymentCreate, ReconciliationCreate


async def _loan_fixture(session: AsyncSession) -> tuple[Organization, Branch, LoanAccount, Cashbox, User, User]:
    suffix = uuid4().hex[:8]
    org = Organization(slug=f"payment-{suffix}", name="Payment Controls")
    maker = User(email=f"maker-{suffix}@example.com", full_name="Finance Maker")
    checker = User(email=f"checker-{suffix}@example.com", full_name="Finance Checker")
    session.add_all([org, maker, checker])
    await session.flush()
    session.add_all(
        [
            Membership(org_id=org.id, user_id=maker.id, role=Role.ADMIN),
            Membership(org_id=org.id, user_id=checker.id, role=Role.ADMIN),
        ]
    )
    branch = Branch(org_id=org.id, code="JKT-01", name="Jakarta", city="Jakarta")
    borrower = Borrower(
        org_id=org.id, customer_reference=f"C-{suffix}", full_name="Nasabah Uji", phone_masked="0812••••0001"
    )
    session.add_all([branch, borrower])
    await session.flush()
    application = LoanApplication(
        org_id=org.id,
        branch_id=branch.id,
        borrower_id=borrower.id,
        application_no=f"PG-{suffix}",
        status="disbursed",
        asset_category="gold",
        requested_amount=Decimal("10000"),
    )
    session.add(application)
    await session.flush()
    loan = LoanAccount(
        org_id=org.id,
        application_id=application.id,
        account_no=f"LN-{suffix}",
        status="active",
        principal_amount=Decimal("9000"),
        total_due_amount=Decimal("10000"),
        outstanding_principal=Decimal("9000"),
        outstanding_fee=Decimal("1000"),
        paid_amount=Decimal("0"),
        disbursed_at=datetime.now(UTC),
    )
    cashbox = Cashbox(org_id=org.id, branch_id=branch.id, code="KAS-01", name="Kas Utama", balance=Decimal("100000"))
    session.add_all([loan, cashbox])
    await session.flush()
    return org, branch, loan, cashbox, maker, checker


async def test_partial_payment_allocates_fee_then_principal_and_is_idempotent(db_session: AsyncSession) -> None:
    org, _branch, loan, cashbox, maker, _checker = await _loan_fixture(db_session)
    data = PaymentCreate(
        loan_account_id=loan.id,
        amount=Decimal("2500"),
        channel="bank_transfer",
        external_reference="BANK-001",
        idempotency_key="payment-test-001",
    )
    receipt = await payment_service.record_payment(db_session, org.id, maker.id, data)
    duplicate = await payment_service.record_payment(db_session, org.id, maker.id, data)
    await db_session.refresh(loan)
    await db_session.refresh(cashbox)

    assert duplicate.id == receipt.id
    assert receipt.allocated_fee == Decimal("1000")
    assert receipt.allocated_principal == Decimal("1500")
    assert loan.outstanding_fee == Decimal("0")
    assert loan.outstanding_principal == Decimal("7500")
    assert cashbox.balance == Decimal("102500")
    lines = list(
        await db_session.scalars(select(JournalLine).where(JournalLine.journal_entry_id == receipt.journal_entry_id))
    )
    assert sum((line.debit_amount for line in lines), Decimal("0")) == Decimal("2500")
    assert sum((line.credit_amount for line in lines), Decimal("0")) == Decimal("2500")


async def test_effective_accounting_policy_changes_payment_waterfall(db_session: AsyncSession) -> None:
    org, _branch, loan, _cashbox, maker, _checker = await _loan_fixture(db_session)
    db_session.add(
        ConfigurationVersion(
            org_id=org.id,
            domain="accounting",
            config_key="payment-allocation",
            version=1,
            status="effective",
            effective_from=datetime.now(UTC),
            payload={"payment_allocation_order": ["principal", "fee"]},
            checksum_sha256="a" * 64,
            change_summary="Alokasikan pembayaran ke pokok sebelum biaya",
            created_by_user_id=maker.id,
            activated_at=datetime.now(UTC),
        )
    )
    await db_session.flush()

    receipt = await payment_service.record_payment(
        db_session,
        org.id,
        maker.id,
        PaymentCreate(
            loan_account_id=loan.id,
            amount=Decimal("2500"),
            channel="bank_transfer",
            external_reference="BANK-PRINCIPAL-FIRST",
            idempotency_key="payment-principal-first",
        ),
    )
    assert receipt.allocated_principal == Decimal("2500")
    assert receipt.allocated_fee == Decimal("0")
    assert loan.outstanding_principal == Decimal("6500")
    assert loan.outstanding_fee == Decimal("1000")


async def test_adjustment_requires_independent_checker_and_posts_contra(db_session: AsyncSession) -> None:
    org, _branch, loan, cashbox, maker, checker = await _loan_fixture(db_session)
    receipt = await payment_service.record_payment(
        db_session,
        org.id,
        maker.id,
        PaymentCreate(
            loan_account_id=loan.id,
            amount=Decimal("2500"),
            channel="bank_transfer",
            external_reference="BANK-002",
            idempotency_key="payment-test-002",
        ),
    )
    adjustment = await payment_service.request_adjustment(
        db_session,
        org.id,
        maker.id,
        PaymentAdjustmentCreate(
            loan_account_id=loan.id,
            payment_receipt_id=receipt.id,
            adjustment_type="refund",
            component="allocation",
            amount=Decimal("1000"),
            reason="Refund salah posting berdasarkan bukti bank",
            external_reference="RF-001",
            idempotency_key="refund-test-001",
        ),
    )
    approval = await db_session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.aggregate_type == "payment_adjustment", ApprovalRequest.aggregate_id == adjustment.id
        )
    )
    assert approval is not None
    with pytest.raises(HTTPException) as same_user:
        await approval_service.decide_approval(
            db_session, org.id, approval.id, maker.id, "approved", "Maker tidak boleh menyetujui refund sendiri"
        )
    assert same_user.value.status_code == 409

    await approval_service.decide_approval(
        db_session, org.id, approval.id, checker.id, "approved", "Bukti mutasi bank dan receipt telah diverifikasi"
    )
    await db_session.refresh(adjustment)
    await db_session.refresh(loan)
    await db_session.refresh(cashbox)
    assert adjustment.status == "posted"
    assert adjustment.allocated_principal == Decimal("1000")
    assert loan.outstanding_principal == Decimal("8500")
    assert loan.paid_amount == Decimal("1500")
    assert cashbox.balance == Decimal("101500")
    journal = await db_session.scalar(select(JournalEntry).where(JournalEntry.id == adjustment.journal_entry_id))
    assert journal is not None and journal.event_type == "refund"


async def test_reconciliation_exception_resolution_is_maker_checker(db_session: AsyncSession) -> None:
    org, branch, loan, _cashbox, maker, checker = await _loan_fixture(db_session)
    await payment_service.record_payment(
        db_session,
        org.id,
        maker.id,
        PaymentCreate(
            loan_account_id=loan.id,
            amount=Decimal("2500"),
            channel="bank_transfer",
            external_reference="BANK-003",
            idempotency_key="payment-test-003",
        ),
    )
    matched = await payment_service.create_reconciliation(
        db_session,
        org.id,
        maker.id,
        ReconciliationCreate(scope="cash_gl", business_date=date.today(), branch_id=branch.id),
    )
    assert matched.status == "matched" and matched.variance_amount == 0
    exception = await payment_service.create_reconciliation(
        db_session,
        org.id,
        maker.id,
        ReconciliationCreate(
            scope="bank_statement",
            business_date=date.today(),
            branch_id=branch.id,
            observed_amount=Decimal("2000"),
            statement_reference="STMT-001",
        ),
    )
    assert exception.status == "exception" and exception.variance_amount == Decimal("-500")
    await payment_service.request_reconciliation_resolution(
        db_session, org.id, maker.id, exception.id, "Selisih berasal dari settlement bank setelah cut-off"
    )
    approval = await db_session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.aggregate_type == "reconciliation", ApprovalRequest.aggregate_id == exception.id
        )
    )
    assert approval is not None
    await approval_service.decide_approval(
        db_session, org.id, approval.id, checker.id, "approved", "Cut-off statement dan bukti settlement sesuai"
    )
    await db_session.refresh(exception)
    assert exception.status == "resolved" and exception.resolved_by_user_id == checker.id


async def test_cash_payment_requires_active_teller_session(db_session: AsyncSession) -> None:
    org, _branch, loan, _cashbox, maker, _checker = await _loan_fixture(db_session)
    with pytest.raises(HTTPException) as missing_session:
        await payment_service.record_payment(
            db_session,
            org.id,
            maker.id,
            PaymentCreate(
                loan_account_id=loan.id,
                amount=Decimal("500"),
                channel="cash",
                external_reference="CASH-001",
                idempotency_key="cash-payment-001",
            ),
        )
    assert missing_session.value.status_code == 409
