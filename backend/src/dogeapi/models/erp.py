"""PrivGadai V3.1 pawn ERP, finance, collection, and reporting models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from dogeapi.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DebtorProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "debtor_profiles"
    __table_args__ = (
        UniqueConstraint("borrower_id", name="uq_debtor_profiles_borrower"),
        ForeignKeyConstraint(
            ["org_id", "borrower_id"],
            ["borrowers.org_id", "borrowers.id"],
            name="fk_debtor_profile_org_borrower",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    borrower_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    national_id_masked: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dati_ii_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    slik_subject_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_status: Mapped[str] = mapped_column(String(24), nullable=False, default="normal", server_default="normal")
    risk_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    internal_watchlist: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="false")
    watchlist_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    correction_status: Mapped[str] = mapped_column(String(24), nullable=False, default="none", server_default="none")


class PawnAgreement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pawn_agreements"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_pawn_agreements_application"),
        UniqueConstraint("org_id", "sbg_number", name="uq_pawn_agreements_org_sbg"),
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_agreement_org_application",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["org_id", "offer_id"],
            ["offers.org_id", "offers.id"],
            name="fk_agreement_org_offer",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    offer_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    sbg_number: Mapped[str] = mapped_column(String(50), nullable=False)
    agreement_type: Mapped[str] = mapped_column(String(24), nullable=False, default="pawn", server_default="pawn")
    document_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="accepted", server_default="accepted")
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    document_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON(), nullable=True)
    consent_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON(), nullable=True)
    document_salt: Mapped[str | None] = mapped_column(String(64), nullable=True)
    document_digest: Mapped[str | None] = mapped_column(String(66), nullable=True)
    consent_digest: Mapped[str | None] = mapped_column(String(66), nullable=True)
    opaque_chain_id: Mapped[str | None] = mapped_column(String(66), nullable=True, unique=True)
    chain_status: Mapped[str] = mapped_column(String(24), nullable=False, default="not_recorded", server_default="not_recorded")
    chain_contract_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    chain_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    chain_block_number: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    chain_attempts: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, server_default="0")
    chain_last_error: Mapped[str | None] = mapped_column(String(240), nullable=True)
    chain_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LoanLedgerEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "loan_ledger_entries"
    __table_args__ = (
        UniqueConstraint("org_id", "idempotency_key", name="uq_loan_ledger_org_idempotency"),
        ForeignKeyConstraint(
            ["org_id", "loan_account_id"],
            ["loan_accounts.org_id", "loan_accounts.id"],
            name="fk_loan_ledger_org_account",
            ondelete="CASCADE",
        ),
        CheckConstraint("debit_amount >= 0 AND credit_amount >= 0", name="ck_loan_ledger_nonnegative"),
        CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0)",
            name="ck_loan_ledger_one_side",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    loan_account_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class GLAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "gl_accounts"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_gl_accounts_org_code"),
        UniqueConstraint("org_id", "id", name="uq_gl_accounts_org_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(24), nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    account_type: Mapped[str] = mapped_column(String(24), nullable=False)
    normal_balance: Mapped[str] = mapped_column(String(8), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="true")


class AccountingPeriod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounting_periods"
    __table_args__ = (
        UniqueConstraint("org_id", "period_start", "period_end", name="uq_accounting_period_range"),
        UniqueConstraint("org_id", "id", name="uq_accounting_period_org_id"),
        CheckConstraint("period_end >= period_start", name="ck_accounting_period_dates"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_start: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open", index=True)
    close_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    closed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JournalEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint("org_id", "entry_no", name="uq_journal_entries_org_number"),
        UniqueConstraint("org_id", "idempotency_key", name="uq_journal_entries_org_idempotency"),
        UniqueConstraint("org_id", "id", name="uq_journal_entries_org_id"),
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_journal_org_application",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    entry_no: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="posted", server_default="posted")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="RESTRICT"), nullable=True
    )
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class JournalLine(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "journal_lines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "journal_entry_id"],
            ["journal_entries.org_id", "journal_entries.id"],
            name="fk_journal_line_org_entry",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["org_id", "account_id"],
            ["gl_accounts.org_id", "gl_accounts.id"],
            name="fk_journal_line_org_account",
            ondelete="RESTRICT",
        ),
        CheckConstraint("debit_amount >= 0 AND credit_amount >= 0", name="ck_journal_line_nonnegative"),
        CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0)",
            name="ck_journal_line_one_side",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Cashbox(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cashboxes"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_cashboxes_org_code"),
        UniqueConstraint("org_id", "id", name="uq_cashboxes_org_id"),
        ForeignKeyConstraint(
            ["org_id", "branch_id"],
            ["branches.org_id", "branches.id"],
            name="fk_cashbox_org_branch",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="true")


class TellerSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teller_sessions"
    __table_args__ = (
        Index(
            "uq_teller_open_cashbox",
            "cashbox_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        ForeignKeyConstraint(
            ["org_id", "cashbox_id"],
            ["cashboxes.org_id", "cashboxes.id"],
            name="fk_teller_session_org_cashbox",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cashbox_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    teller_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open", index=True)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    expected_closing_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    actual_closing_balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    variance_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    variance_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    variance_approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    variance_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CashTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cash_transactions"
    __table_args__ = (
        UniqueConstraint("org_id", "idempotency_key", name="uq_cash_transactions_org_idempotency"),
        ForeignKeyConstraint(
            ["org_id", "cashbox_id"],
            ["cashboxes.org_id", "cashboxes.id"],
            name="fk_cash_tx_org_cashbox",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["org_id", "loan_account_id"],
            ["loan_accounts.org_id", "loan_accounts.id"],
            name="fk_cash_tx_org_loan",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["org_id", "journal_entry_id"],
            ["journal_entries.org_id", "journal_entries.id"],
            name="fk_cash_tx_org_journal",
            ondelete="RESTRICT",
        ),
        CheckConstraint("amount > 0", name="ck_cash_transaction_positive"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cashbox_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    teller_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("teller_sessions.id", ondelete="RESTRICT"), nullable=True
    )
    loan_account_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    external_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CollectionCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "collection_cases"
    __table_args__ = (
        UniqueConstraint("loan_account_id", name="uq_collection_cases_loan"),
        UniqueConstraint("org_id", "id", name="uq_collection_cases_org_id"),
        ForeignKeyConstraint(
            ["org_id", "loan_account_id"],
            ["loan_accounts.org_id", "loan_accounts.id"],
            name="fk_collection_case_org_loan",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    loan_account_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    outstanding_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    aging_bucket: Mapped[str] = mapped_column(String(24), nullable=False, default="current", server_default="current")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="monitoring", server_default="monitoring")
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="reminder", server_default="reminder")
    stage: Mapped[str] = mapped_column(
        String(32), nullable=False, default="soft_collection", server_default="soft_collection"
    )
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CollectionNote(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "collection_notes"

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collection_case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("collection_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    note: Mapped[str] = mapped_column(Text(), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CollectionPromise(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "collection_promises"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_collection_promise_amount_positive"),
        ForeignKeyConstraint(
            ["org_id", "collection_case_id"],
            ["collection_cases.org_id", "collection_cases.id"],
            name="fk_collection_promise_org_case",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collection_case_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    promised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending", server_default="pending", index=True
    )
    note: Mapped[str] = mapped_column(Text(), nullable=False)
    resolution_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RegulatoryReportTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regulatory_report_templates"
    __table_args__ = (
        UniqueConstraint("org_id", "report_type", "code", "version", name="uq_reg_template_version"),
        UniqueConstraint("org_id", "id", name="uq_reg_templates_org_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date(), nullable=False)
    mapping_schema: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, default=dict)
    validation_rules: Mapped[list[dict[str, object]]] = mapped_column(JSON(), nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default="draft")


class RegulatoryReportRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "regulatory_report_runs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "template_id"],
            ["regulatory_report_templates.org_id", "regulatory_report_templates.id"],
            name="fk_reg_run_org_template",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date(), nullable=False)
    period_end: Mapped[date] = mapped_column(Date(), nullable=False)
    revision: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default="draft", index=True)
    validation_results: Mapped[list[dict[str, object]]] = mapped_column(JSON(), nullable=False, default=list)
    report_payload: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, default=dict)
    sensitive_payload_ciphertext: Mapped[str | None] = mapped_column(Text(), nullable=True)
    generated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InventoryCheck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inventory_checks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "location_id"],
            ["custody_locations.org_id", "custody_locations.id"],
            name="fk_inventory_check_org_location",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("org_id", "id", name="uq_inventory_checks_org_id"),
        Index(
            "uq_inventory_active_location",
            "location_id",
            unique=True,
            postgresql_where=text("status IN ('draft', 'recount_required', 'submitted')"),
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    performed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    recounted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default="draft")
    counted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    recounted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InventoryCheckItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "inventory_check_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "inventory_check_id"],
            ["inventory_checks.org_id", "inventory_checks.id"],
            name="fk_inventory_item_org_check",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_inventory_item_org_application",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("inventory_check_id", "application_id", name="uq_inventory_item_application"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inventory_check_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    expected_status: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result: Mapped[str | None] = mapped_column(String(24), nullable=True)
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    recount_observed_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recount_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
