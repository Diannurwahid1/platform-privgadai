"""Blind inventory snapshots and independent recount.

Revision ID: 5fb0316c8da4
Revises: 4eaf205b7c93
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5fb0316c8da4"
down_revision: str | None = "4eaf205b7c93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("inventory_checks", sa.Column("recounted_by_user_id", sa.UUID(), nullable=True))
    op.add_column("inventory_checks", sa.Column("recounted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_inventory_recounted_by",
        "inventory_checks",
        "users",
        ["recounted_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.alter_column("inventory_check_items", "observed_status", existing_type=sa.String(32), nullable=True)
    op.alter_column("inventory_check_items", "result", existing_type=sa.String(24), nullable=True)
    op.add_column("inventory_check_items", sa.Column("recount_observed_status", sa.String(32), nullable=True))
    op.add_column("inventory_check_items", sa.Column("recount_note", sa.Text(), nullable=True))
    op.create_index(
        "uq_inventory_active_location",
        "inventory_checks",
        ["location_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('draft', 'recount_required', 'submitted')"),
    )


def downgrade() -> None:
    op.drop_index("uq_inventory_active_location", table_name="inventory_checks")
    op.drop_column("inventory_check_items", "recount_note")
    op.drop_column("inventory_check_items", "recount_observed_status")
    op.execute("UPDATE inventory_check_items SET observed_status = 'unknown' WHERE observed_status IS NULL")
    op.execute("UPDATE inventory_check_items SET result = 'variance' WHERE result IS NULL")
    op.alter_column("inventory_check_items", "result", existing_type=sa.String(24), nullable=False)
    op.alter_column("inventory_check_items", "observed_status", existing_type=sa.String(32), nullable=False)
    op.drop_constraint("fk_inventory_recounted_by", "inventory_checks", type_="foreignkey")
    op.drop_column("inventory_checks", "recounted_at")
    op.drop_column("inventory_checks", "recounted_by_user_id")
