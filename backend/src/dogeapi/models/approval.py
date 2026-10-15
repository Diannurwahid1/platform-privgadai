"""Generic four-eyes approval ledger."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from dogeapi.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ApprovalRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        UniqueConstraint("org_id", "id", name="uq_approval_requests_org_id"),
        UniqueConstraint(
            "org_id", "aggregate_type", "aggregate_id", "action", "version", name="uq_approval_request_version"
        ),
        ForeignKeyConstraint(
            ["org_id", "branch_id"],
            ["branches.org_id", "branches.id"],
            name="fk_approval_request_org_branch",
            ondelete="RESTRICT",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    aggregate_reference: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1, server_default="1")
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_role: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending", server_default="pending", index=True
    )
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal", server_default="normal")
    request_reason: Mapped[str] = mapped_column(Text(), nullable=False)
    payload_snapshot: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False, default=dict)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)


class ApprovalEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "approval_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "approval_id"],
            ["approval_requests.org_id", "approval_requests.id"],
            name="fk_approval_event_org_request",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    approval_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
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
