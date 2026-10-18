"""Versioned AI estimates and verified local valuation comparables."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from dogeapi.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AppraisalComparable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "appraisal_comparables"
    __table_args__ = (UniqueConstraint("org_id", "id", name="uq_appraisal_comparable_org_id"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    condition_grade: Mapped[str] = mapped_column(String(24), nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    source_label: Mapped[str] = mapped_column(String(200), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")


class AiAppraisalEstimate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_appraisal_estimates"
    __table_args__ = (
        UniqueConstraint("org_id", "id", name="uq_ai_appraisal_estimate_org_id"),
        ForeignKeyConstraint(
            ["org_id", "borrower_id"],
            ["borrowers.org_id", "borrowers.id"],
            name="fk_ai_estimate_org_borrower",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_ai_estimate_org_application",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    borrower_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    application_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    category_code: Mapped[str] = mapped_column(String(40), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    asset_description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    condition_grade: Mapped[str] = mapped_column(String(24), nullable=False)
    photo_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    photo_key: Mapped[str] = mapped_column(String(500), nullable=False)
    photo_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    photo_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    quality_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    quality_findings: Mapped[list[str]] = mapped_column(JSON(), nullable=False, default=list)
    vision_result: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, default=dict)
    research_result: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, default=dict)
    vision_status: Mapped[str] = mapped_column(String(24), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    estimator_version: Mapped[str] = mapped_column(String(40), nullable=False)
    low_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    high_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    comparable_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    comparable_ids: Mapped[list[str]] = mapped_column(JSON(), nullable=False, default=list)
    explanation: Mapped[str] = mapped_column(Text(), nullable=False)
