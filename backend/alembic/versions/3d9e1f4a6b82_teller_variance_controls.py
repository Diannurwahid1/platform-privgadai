"""Teller variance controls and exclusive cashbox sessions.

Revision ID: 3d9e1f4a6b82
Revises: 2c8d0e3f5a71
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3d9e1f4a6b82"
down_revision: str | None = "2c8d0e3f5a71"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("teller_sessions", sa.Column("variance_amount", sa.Numeric(18, 2), nullable=True))
    op.add_column("teller_sessions", sa.Column("variance_reason", sa.Text(), nullable=True))
    op.add_column("teller_sessions", sa.Column("variance_approved_by_user_id", sa.UUID(), nullable=True))
    op.add_column("teller_sessions", sa.Column("variance_approved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_teller_variance_approved_by",
        "teller_sessions",
        "users",
        ["variance_approved_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "uq_teller_open_cashbox",
        "teller_sessions",
        ["cashbox_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    op.drop_index("uq_teller_open_cashbox", table_name="teller_sessions")
    op.drop_constraint("fk_teller_variance_approved_by", "teller_sessions", type_="foreignkey")
    op.drop_column("teller_sessions", "variance_approved_at")
    op.drop_column("teller_sessions", "variance_approved_by_user_id")
    op.drop_column("teller_sessions", "variance_reason")
    op.drop_column("teller_sessions", "variance_amount")
