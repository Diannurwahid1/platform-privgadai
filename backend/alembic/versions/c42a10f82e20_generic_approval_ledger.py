"""Generic approval ledger.

Revision ID: c42a10f82e20
Revises: b31f0a2c7d11
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c42a10f82e20"
down_revision: str | None = "b31f0a2c7d11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("org_id", sa.UUID(), nullable=False), sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("aggregate_type", sa.String(40), nullable=False), sa.Column("aggregate_id", sa.UUID(), nullable=False),
        sa.Column("aggregate_reference", sa.String(80), nullable=False), sa.Column("action", sa.String(60), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=False), sa.Column("assigned_role", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("priority", sa.String(16), server_default="normal", nullable=False),
        sa.Column("request_reason", sa.Text(), nullable=False), sa.Column("payload_snapshot", sa.JSON(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True), sa.Column("decided_by_user_id", sa.UUID(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True), sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id", "branch_id"], ["branches.org_id", "branches.id"], name="fk_approval_request_org_branch", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("org_id", "id", name="uq_approval_requests_org_id"),
        sa.UniqueConstraint("org_id", "aggregate_type", "aggregate_id", "action", "version", name="uq_approval_request_version"),
    )
    for column in ("org_id", "branch_id", "aggregate_type", "aggregate_id", "action", "requested_by_user_id", "status"):
        op.create_index(f"ix_approval_requests_{column}", "approval_requests", [column])
    op.create_table(
        "approval_events",
        sa.Column("org_id", sa.UUID(), nullable=False), sa.Column("approval_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True), sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(24), nullable=True), sa.Column("to_status", sa.String(24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True), sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id", "approval_id"], ["approval_requests.org_id", "approval_requests.id"], name="fk_approval_event_org_request", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_events_org_id", "approval_events", ["org_id"])
    op.create_index("ix_approval_events_approval_id", "approval_events", ["approval_id"])
    op.create_index("ix_approval_events_occurred_at", "approval_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("approval_events")
    op.drop_table("approval_requests")
