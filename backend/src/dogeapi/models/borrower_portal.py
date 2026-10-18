"""Borrower-only identity and revocable browser sessions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from dogeapi.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BorrowerAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "borrower_accounts"
    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_borrower_account_org_email"),
        UniqueConstraint("org_id", "borrower_id", name="uq_borrower_account_org_borrower"),
        ForeignKeyConstraint(
            ["org_id", "borrower_id"],
            ["borrowers.org_id", "borrowers.id"],
            name="fk_borrower_account_org_borrower",
            ondelete="CASCADE",
        ),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    borrower_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone_ciphertext: Mapped[str] = mapped_column(String(500), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(300), nullable=False)


class BorrowerSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "borrower_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_borrower_session_token_hash"),
        ForeignKeyConstraint(["account_id"], ["borrower_accounts.id"], ondelete="CASCADE"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
