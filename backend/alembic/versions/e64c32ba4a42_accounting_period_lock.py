"""Accounting period lock.

Revision ID: e64c32ba4a42
Revises: d53b21a93f31
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e64c32ba4a42"
down_revision: str | None = "d53b21a93f31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounting_periods",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(24), server_default="open", nullable=False),
        sa.Column("close_reason", sa.Text(), nullable=True),
        sa.Column("closed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("period_end >= period_start", name="ck_accounting_period_dates"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["closed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id", name="uq_accounting_period_org_id"),
        sa.UniqueConstraint("org_id", "period_start", "period_end", name="uq_accounting_period_range"),
    )
    for column in ("org_id", "period_start", "period_end", "status"):
        op.create_index(f"ix_accounting_periods_{column}", "accounting_periods", [column])


def downgrade() -> None:
    op.drop_table("accounting_periods")
