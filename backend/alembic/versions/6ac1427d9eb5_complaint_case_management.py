"""Complaint case management and SLA events.

Revision ID: 6ac1427d9eb5
Revises: 5fb0316c8da4
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6ac1427d9eb5"
down_revision: str | None = "5fb0316c8da4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "complaint_cases",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("ticket_no", sa.String(40), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("borrower_id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=True),
        sa.Column("reported_by_user_id", sa.UUID(), nullable=False),
        sa.Column("assigned_to_user_id", sa.UUID(), nullable=True),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("channel", sa.String(24), nullable=False),
        sa.Column("priority", sa.String(16), server_default="normal", nullable=False),
        sa.Column("status", sa.String(24), server_default="new", nullable=False),
        sa.Column("subject", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("vulnerable_customer", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("regulator_reportable", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("response_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("outcome", sa.String(32), nullable=True),
        sa.Column("compensation_amount", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("resolved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalation_level", sa.Integer(), server_default="0", nullable=False),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reopened_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reported_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["org_id", "branch_id"],
            ["branches.org_id", "branches.id"],
            name="fk_complaint_org_branch",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "borrower_id"],
            ["borrowers.org_id", "borrowers.id"],
            name="fk_complaint_org_borrower",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_complaint_org_application",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "ticket_no", name="uq_complaints_org_ticket"),
        sa.UniqueConstraint("org_id", "id", name="uq_complaints_org_id"),
    )
    for column in (
        "org_id",
        "branch_id",
        "borrower_id",
        "application_id",
        "assigned_to_user_id",
        "category",
        "status",
        "response_due_at",
        "resolution_due_at",
    ):
        op.create_index(f"ix_complaint_cases_{column}", "complaint_cases", [column])
    op.create_table(
        "complaint_events",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("complaint_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("direction", sa.String(16), nullable=True),
        sa.Column("channel", sa.String(24), nullable=True),
        sa.Column("from_status", sa.String(24), nullable=True),
        sa.Column("to_status", sa.String(24), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["org_id", "complaint_id"],
            ["complaint_cases.org_id", "complaint_cases.id"],
            name="fk_complaint_event_org_case",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_complaint_events_org_id", "complaint_events", ["org_id"])
    op.create_index("ix_complaint_events_complaint_id", "complaint_events", ["complaint_id"])


def downgrade() -> None:
    op.drop_index("ix_complaint_events_complaint_id", table_name="complaint_events")
    op.drop_index("ix_complaint_events_org_id", table_name="complaint_events")
    op.drop_table("complaint_events")
    for column in reversed(
        (
            "org_id",
            "branch_id",
            "borrower_id",
            "application_id",
            "assigned_to_user_id",
            "category",
            "status",
            "response_due_at",
            "resolution_due_at",
        )
    ):
        op.drop_index(f"ix_complaint_cases_{column}", table_name="complaint_cases")
    op.drop_table("complaint_cases")
