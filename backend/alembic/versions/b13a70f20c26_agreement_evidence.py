"""Freeze borrower agreement evidence and track BSC Testnet anchoring.

Revision ID: b13a70f20c26
Revises: a84c6b5d97e1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b13a70f20c26"
down_revision: str | Sequence[str] | None = "a84c6b5d97e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pawn_agreements", sa.Column("document_snapshot", sa.JSON(), nullable=True))
    op.add_column("pawn_agreements", sa.Column("consent_snapshot", sa.JSON(), nullable=True))
    op.add_column("pawn_agreements", sa.Column("document_salt", sa.String(64), nullable=True))
    op.add_column("pawn_agreements", sa.Column("document_digest", sa.String(66), nullable=True))
    op.add_column("pawn_agreements", sa.Column("consent_digest", sa.String(66), nullable=True))
    op.add_column("pawn_agreements", sa.Column("opaque_chain_id", sa.String(66), nullable=True))
    op.add_column("pawn_agreements", sa.Column("chain_status", sa.String(24), nullable=False, server_default="not_recorded"))
    op.add_column("pawn_agreements", sa.Column("chain_contract_address", sa.String(42), nullable=True))
    op.add_column("pawn_agreements", sa.Column("chain_tx_hash", sa.String(66), nullable=True))
    op.add_column("pawn_agreements", sa.Column("chain_block_number", sa.Integer(), nullable=True))
    op.add_column("pawn_agreements", sa.Column("chain_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("pawn_agreements", sa.Column("chain_last_error", sa.String(240), nullable=True))
    op.add_column("pawn_agreements", sa.Column("chain_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_pawn_agreements_opaque_chain_id", "pawn_agreements", ["opaque_chain_id"])
    op.execute("UPDATE pawn_agreements SET status = 'legacy_acceptance' WHERE status = 'signed'")
    op.alter_column("pawn_agreements", "status", server_default="accepted")


def downgrade() -> None:
    op.alter_column("pawn_agreements", "status", server_default="signed")
    op.execute("UPDATE pawn_agreements SET status = 'signed' WHERE status = 'legacy_acceptance'")
    op.drop_constraint("uq_pawn_agreements_opaque_chain_id", "pawn_agreements", type_="unique")
    for column in (
        "chain_confirmed_at", "chain_last_error", "chain_attempts", "chain_block_number",
        "chain_tx_hash", "chain_contract_address", "chain_status", "opaque_chain_id",
        "consent_digest", "document_digest", "document_salt", "consent_snapshot", "document_snapshot",
    ):
        op.drop_column("pawn_agreements", column)
