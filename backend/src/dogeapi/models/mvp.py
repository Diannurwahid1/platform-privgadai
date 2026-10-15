"""PrivGadai MVP domain models beyond application intake."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from dogeapi.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AssetCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_categories"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_asset_categories_org_code"),
        UniqueConstraint("org_id", "id", name="uq_asset_categories_org_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    requires_serial_number: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="true")


class LoanProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "loan_products"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_loan_products_org_code"),
        UniqueConstraint("org_id", "id", name="uq_loan_products_org_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    max_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    max_ltv_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    allowed_tenors_days: Mapped[list[int]] = mapped_column(JSON(), nullable=False)
    service_fee_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="true")


class StaffAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "staff_assignments"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", "branch_id", "operational_role", name="uq_staff_assignment"),
        ForeignKeyConstraint(
            ["org_id", "branch_id"],
            ["branches.org_id", "branches.id"],
            name="fk_staff_org_branch",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["user_id", "org_id"],
            ["memberships.user_id", "memberships.org_id"],
            name="fk_staff_user_membership",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    operational_role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="true")


class Consent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "consents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "borrower_id"],
            ["borrowers.org_id", "borrowers.id"],
            name="fk_consents_org_borrower",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    borrower_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    consent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_version: Mapped[str] = mapped_column(String(32), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="web", server_default="web")


class EvidenceFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evidence_files"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_evidence_org_application",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(40), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer(), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    scan_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")


class HumanAppraisal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "human_appraisals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_appraisals_org_application",
            ondelete="CASCADE",
        ),
        UniqueConstraint("application_id", "revision", name="uq_appraisal_revision"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    appraiser_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    revision: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    liquidation_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    recommended_loan: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    condition_grade: Mapped[str] = mapped_column(String(24), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="final", server_default="final")


class Offer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "offers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_offers_org_application",
            ondelete="CASCADE",
        ),
        UniqueConstraint("application_id", "version", name="uq_offer_version"),
        UniqueConstraint("org_id", "id", name="uq_offers_org_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tenor_days: Mapped[int] = mapped_column(Integer(), nullable=False)
    service_fee_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_due_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    agreement_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="offered", server_default="offered")


class CustomerAcceptance(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "customer_acceptances"
    __table_args__ = (
        UniqueConstraint("offer_id", name="uq_customer_acceptance_offer"),
        ForeignKeyConstraint(
            ["org_id", "offer_id"],
            ["offers.org_id", "offers.id"],
            name="fk_acceptance_org_offer",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["org_id", "borrower_id"],
            ["borrowers.org_id", "borrowers.id"],
            name="fk_acceptance_org_borrower",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    borrower_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="web", server_default="web")
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PickupTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "pickup_tasks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_pickup_org_application",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="assigned", server_default="assigned")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pickup_address: Mapped[str] = mapped_column(Text(), nullable=False)
    assignment_code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    condition_note: Mapped[str | None] = mapped_column(Text(), nullable=True)


class CustodyLocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "custody_locations"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_custody_locations_org_code"),
        UniqueConstraint("org_id", "id", name="uq_custody_locations_org_id"),
        ForeignKeyConstraint(
            ["org_id", "branch_id"],
            ["branches.org_id", "branches.id"],
            name="fk_custody_location_org_branch",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    location_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True, server_default="true")


class CustodyEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "custody_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_custody_event_org_application",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["org_id", "location_id"],
            ["custody_locations.org_id", "custody_locations.id"],
            name="fk_custody_event_org_location",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    location_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    condition_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SettlementVerification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "settlement_verifications"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_settlement_org_application",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    verified_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    settlement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    external_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="verified", server_default="verified")
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LoanAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "loan_accounts"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_loan_accounts_application"),
        UniqueConstraint("org_id", "id", name="uq_loan_accounts_org_id"),
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_loan_account_org_application",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    account_no: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="awaiting_disbursement", server_default="awaiting_disbursement", index=True
    )
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_due_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    disbursement_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disbursed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Incident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_incident_org_application",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    reported_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    incident_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", server_default="medium")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open", index=True)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    resolution_note: Mapped[str | None] = mapped_column(Text(), nullable=True)


class CollateralEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "collateral_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_collateral_event_org_application",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    event_metadata: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
