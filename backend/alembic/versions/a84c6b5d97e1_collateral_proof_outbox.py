"""Add transactional BSC custody proof outbox.

Revision ID: a84c6b5d97e1
Revises: f36a91c82d70
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a84c6b5d97e1"
down_revision: str | Sequence[str] | None = "f36a91c82d70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collateral_proofs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collateral_event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("collateral_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("opaque_event_id", sa.String(66), nullable=False),
        sa.Column("digest", sa.String(66), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("salt", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("chain_id", sa.Integer(), nullable=False, server_default="97"),
        sa.Column("contract_address", sa.String(42)),
        sa.Column("tx_hash", sa.String(66)),
        sa.Column("block_number", sa.Integer()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(240)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["org_id", "application_id"], ["loan_applications.org_id", "loan_applications.id"], name="fk_proof_org_application", ondelete="CASCADE"),
        sa.UniqueConstraint("collateral_event_id", name="uq_proof_collateral_event"),
        sa.UniqueConstraint("opaque_event_id", name="uq_proof_opaque_event"),
    )
    op.create_index("ix_collateral_proofs_org_id", "collateral_proofs", ["org_id"])
    op.create_index("ix_collateral_proofs_application_id", "collateral_proofs", ["application_id"])


def downgrade() -> None:
    op.drop_index("ix_collateral_proofs_application_id", table_name="collateral_proofs")
    op.drop_index("ix_collateral_proofs_org_id", table_name="collateral_proofs")
    op.drop_table("collateral_proofs")
