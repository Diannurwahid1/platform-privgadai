"""Two-stage custody movements.

Revision ID: f75d43cb5b53
Revises: e64c32ba4a42
Create Date: 2026-10-16
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "f75d43cb5b53"
down_revision: str | None = "e64c32ba4a42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "custody_movements",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("movement_no", sa.String(50), nullable=False),
        sa.Column("from_location_id", sa.UUID(), nullable=False),
        sa.Column("to_location_id", sa.UUID(), nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=False),
        sa.Column("dispatched_by_user_id", sa.UUID(), nullable=True),
        sa.Column("received_by_user_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(24), server_default="requested", nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("seal_out", sa.String(80), nullable=True),
        sa.Column("seal_in", sa.String(80), nullable=True),
        sa.Column("dispatch_note", sa.Text(), nullable=True),
        sa.Column("receipt_note", sa.Text(), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["org_id", "application_id"], ["loan_applications.org_id", "loan_applications.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "from_location_id"],
            ["custody_locations.org_id", "custody_locations.id"],
            name="fk_movement_from_location",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "to_location_id"],
            ["custody_locations.org_id", "custody_locations.id"],
            name="fk_movement_to_location",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dispatched_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["received_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "movement_no", name="uq_custody_movement_number"),
    )
    for column in ("org_id", "application_id", "status"):
        op.create_index(f"ix_custody_movements_{column}", "custody_movements", [column])


def downgrade() -> None:
    op.drop_table("custody_movements")
