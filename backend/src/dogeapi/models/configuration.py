"""Versioned and effective-dated tenant configuration models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from dogeapi.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConfigurationVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "configuration_versions"
    __table_args__ = (
        UniqueConstraint("org_id", "domain", "config_key", "version", name="uq_configuration_version"),
        UniqueConstraint("org_id", "id", name="uq_configuration_org_id"),
        Index(
            "uq_configuration_effective_key",
            "org_id",
            "domain",
            "config_key",
            unique=True,
            postgresql_where=text("status = 'effective'"),
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    config_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default="draft", index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    change_summary: Mapped[str] = mapped_column(Text(), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("configuration_versions.id", ondelete="SET NULL"), nullable=True
    )


class ConfigurationEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "configuration_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "configuration_id"],
            ["configuration_versions.org_id", "configuration_versions.id"],
            name="fk_configuration_event_org_version",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    configuration_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
