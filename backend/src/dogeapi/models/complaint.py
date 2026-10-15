"""Customer complaint and support case models."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
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


class ComplaintCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "complaint_cases"
    __table_args__ = (
        UniqueConstraint("org_id", "ticket_no", name="uq_complaints_org_ticket"),
        UniqueConstraint("org_id", "id", name="uq_complaints_org_id"),
        ForeignKeyConstraint(
            ["org_id", "branch_id"],
            ["branches.org_id", "branches.id"],
            name="fk_complaint_org_branch",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["org_id", "borrower_id"],
            ["borrowers.org_id", "borrowers.id"],
            name="fk_complaint_org_borrower",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_complaint_org_application",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_no: Mapped[str] = mapped_column(String(40), nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    borrower_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    application_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    reported_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal", server_default="normal")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="new", server_default="new", index=True)
    subject: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    vulnerable_customer: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="false")
    regulator_reportable: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, server_default="false")
    response_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    resolution_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text(), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    compensation_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0, server_default="0")
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalation_level: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, server_default="0")
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopened_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, server_default="0")


class ComplaintEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "complaint_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "complaint_id"],
            ["complaint_cases.org_id", "complaint_cases.id"],
            name="fk_complaint_event_org_case",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    complaint_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    direction: Mapped[str | None] = mapped_column(String(16), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(24), nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
