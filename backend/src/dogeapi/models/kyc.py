"""Customer due diligence records for PrivGadai."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
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


class KycVerification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "kyc_verifications"
    __table_args__ = (
        UniqueConstraint("org_id", "id", name="uq_kyc_verifications_org_id"),
        ForeignKeyConstraint(
            ["org_id", "borrower_id"],
            ["borrowers.org_id", "borrowers.id"],
            name="fk_kyc_verification_org_borrower",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    borrower_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    initiated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    document_type: Mapped[str] = mapped_column(String(24), nullable=False, default="ktp", server_default="ktp")
    nik_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    national_id_ciphertext: Mapped[str | None] = mapped_column(Text(), nullable=True)
    national_id_masked: Mapped[str] = mapped_column(String(32), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(180), nullable=False)
    birth_place: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date(), nullable=False)
    gender: Mapped[str] = mapped_column(String(16), nullable=False)
    address: Mapped[str] = mapped_column(Text(), nullable=False)
    province: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    occupation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nationality: Mapped[str] = mapped_column(String(3), nullable=False, default="IDN", server_default="IDN")
    verification_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual_branch", server_default="manual_branch"
    )
    provider_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending_documents", server_default="pending_documents", index=True
    )
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="standard", server_default="standard")
    face_match_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    liveness_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    document_authenticity_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    pep_match: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="false")
    sanctions_match: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="false")
    decision_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KycDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "kyc_documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "verification_id"],
            ["kyc_verifications.org_id", "kyc_verifications.id"],
            name="fk_kyc_document_org_verification",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    verification_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    document_side: Mapped[str] = mapped_column(String(24), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    encryption_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="fernet-v1", server_default="fernet-v1"
    )
    scan_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    scanner_engine: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scan_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quarantined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KycEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "kyc_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "verification_id"],
            ["kyc_verifications.org_id", "kyc_verifications.id"],
            name="fk_kyc_event_org_verification",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    verification_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_status: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class KycProviderCheck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable evidence of an OCR or identity-provider call."""

    __tablename__ = "kyc_provider_checks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "verification_id"],
            ["kyc_verifications.org_id", "kyc_verifications.id"],
            name="fk_kyc_provider_check_org_verification",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    verification_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    check_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(80), nullable=False)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    response_ciphertext: Mapped[str] = mapped_column(Text(), nullable=False)
    internal_verified: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="false")
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
