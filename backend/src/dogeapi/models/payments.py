"""Controlled payment, adjustment, and reconciliation records."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from dogeapi.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PaymentReceipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_receipts"
    __table_args__ = (
        UniqueConstraint("org_id", "id", name="uq_payment_receipts_org_id"),
        UniqueConstraint("org_id", "receipt_no", name="uq_payment_receipts_org_number"),
        UniqueConstraint("org_id", "idempotency_key", name="uq_payment_receipts_org_idempotency"),
        ForeignKeyConstraint(
            ["org_id", "loan_account_id"],
            ["loan_accounts.org_id", "loan_accounts.id"],
            name="fk_payment_receipt_org_loan",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["org_id", "cashbox_id"],
            ["cashboxes.org_id", "cashboxes.id"],
            name="fk_payment_receipt_org_cashbox",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["org_id", "journal_entry_id"],
            ["journal_entries.org_id", "journal_entries.id"],
            name="fk_payment_receipt_org_journal",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    loan_account_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    cashbox_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    teller_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("teller_sessions.id", ondelete="RESTRICT"), nullable=True
    )
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    receipt_no: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    allocated_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    allocated_principal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="posted", server_default="posted", index=True
    )
    external_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    received_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PaymentAdjustment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_adjustments"
    __table_args__ = (
        UniqueConstraint("org_id", "id", name="uq_payment_adjustments_org_id"),
        UniqueConstraint("org_id", "idempotency_key", name="uq_payment_adjustments_org_idempotency"),
        ForeignKeyConstraint(
            ["org_id", "loan_account_id"],
            ["loan_accounts.org_id", "loan_accounts.id"],
            name="fk_payment_adjustment_org_loan",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["org_id", "payment_receipt_id"],
            ["payment_receipts.org_id", "payment_receipts.id"],
            name="fk_payment_adjustment_org_receipt",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    loan_account_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    payment_receipt_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="RESTRICT"), nullable=True
    )
    cash_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cash_transactions.id", ondelete="RESTRICT"), nullable=True
    )
    adjustment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    component: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    allocated_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    allocated_principal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending_approval", server_default="pending_approval", index=True
    )
    reason: Mapped[str] = mapped_column(Text(), nullable=False)
    external_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReconciliationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reconciliation_runs"
    __table_args__ = (UniqueConstraint("org_id", "id", name="uq_reconciliation_runs_org_id"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("branches.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    business_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    observed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    variance_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tolerance_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    exception_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    snapshot: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, default=dict)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    resolution_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
