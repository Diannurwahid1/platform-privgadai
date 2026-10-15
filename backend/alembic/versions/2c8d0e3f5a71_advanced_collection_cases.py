"""Advanced collection cases and promises to pay.

Revision ID: 2c8d0e3f5a71
Revises: 1b7c9d2e4f60
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2c8d0e3f5a71"
down_revision: str | None = "1b7c9d2e4f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("collection_cases", sa.Column("strategy", sa.String(32), server_default="reminder", nullable=False))
    op.add_column(
        "collection_cases", sa.Column("stage", sa.String(32), server_default="soft_collection", nullable=False)
    )
    op.add_column("collection_cases", sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_collection_cases_org_id", "collection_cases", ["org_id", "id"])
    op.create_table(
        "collection_promises",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("collection_case_id", sa.UUID(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("resolved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("promised_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("channel", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["org_id", "collection_case_id"],
            ["collection_cases.org_id", "collection_cases.id"],
            name="fk_collection_promise_org_case",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount > 0", name="ck_collection_promise_amount_positive"),
    )
    for column in ("org_id", "collection_case_id", "promised_at", "status"):
        op.create_index(f"ix_collection_promises_{column}", "collection_promises", [column])


def downgrade() -> None:
    op.drop_table("collection_promises")
    op.drop_constraint("uq_collection_cases_org_id", "collection_cases", type_="unique")
    op.drop_column("collection_cases", "last_contact_at")
    op.drop_column("collection_cases", "stage")
    op.drop_column("collection_cases", "strategy")
