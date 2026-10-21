"""Transactional outbox for custody commitments on BSC Testnet."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from dogeapi.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CollateralProof(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "collateral_proofs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_proof_org_application",
            ondelete="CASCADE",
        ),
        UniqueConstraint("collateral_event_id", name="uq_proof_collateral_event"),
        UniqueConstraint("opaque_event_id", name="uq_proof_opaque_event"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("organizations.id"), index=True)
    application_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    collateral_event_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("collateral_events.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    opaque_event_id: Mapped[str] = mapped_column(String(66), nullable=False)
    digest: Mapped[str] = mapped_column(String(66), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON(), nullable=False)
    salt: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    chain_id: Mapped[int] = mapped_column(Integer(), nullable=False, default=97, server_default="97")
    contract_address: Mapped[str | None] = mapped_column(String(42), nullable=True)
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    block_number: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(String(240), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
