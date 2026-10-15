"""Approval delegation and escalation controls.

Revision ID: 0a9e7c24d801
Revises: f75d43cb5b53
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0a9e7c24d801"
down_revision: str | None = "f75d43cb5b53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "approval_delegations",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("delegator_user_id", sa.UUID(), nullable=False),
        sa.Column("delegate_user_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=True),
        sa.Column("assigned_role", sa.String(40), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("delegator_user_id <> delegate_user_id", name="ck_approval_delegation_distinct_users"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["org_id", "branch_id"],
            ["branches.org_id", "branches.id"],
            name="fk_approval_delegation_org_branch",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["delegator_user_id", "org_id"],
            ["memberships.user_id", "memberships.org_id"],
            name="fk_approval_delegator_membership",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["delegate_user_id", "org_id"],
            ["memberships.user_id", "memberships.org_id"],
            name="fk_approval_delegate_membership",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("org_id", "delegator_user_id", "delegate_user_id", "branch_id", "assigned_role"):
        op.create_index(f"ix_approval_delegations_{column}", "approval_delegations", [column])

    op.add_column("approval_requests", sa.Column("escalation_level", sa.Integer(), server_default="0", nullable=False))
    op.add_column("approval_requests", sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("approval_requests", sa.Column("decided_under_delegation_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_approval_request_decision_delegation",
        "approval_requests",
        "approval_delegations",
        ["decided_under_delegation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_approval_request_decision_delegation", "approval_requests", type_="foreignkey")
    op.drop_column("approval_requests", "decided_under_delegation_id")
    op.drop_column("approval_requests", "escalated_at")
    op.drop_column("approval_requests", "escalation_level")
    op.drop_table("approval_delegations")
