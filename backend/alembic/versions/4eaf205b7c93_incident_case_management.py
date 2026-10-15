"""Incident investigation and resolution workflow.

Revision ID: 4eaf205b7c93
Revises: 3d9e1f4a6b82
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4eaf205b7c93"
down_revision: str | None = "3d9e1f4a6b82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_incidents_org_id", "incidents", ["org_id", "id"])
    op.add_column("incidents", sa.Column("assigned_to_user_id", sa.UUID(), nullable=True))
    op.add_column("incidents", sa.Column("root_cause", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("action_plan", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("resolved_by_user_id", sa.UUID(), nullable=True))
    op.add_column("incidents", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("reopened_count", sa.Integer(), server_default="0", nullable=False))
    op.create_foreign_key(
        "fk_incident_assignee", "incidents", "users", ["assigned_to_user_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_incident_resolver", "incidents", "users", ["resolved_by_user_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_incidents_assigned_to_user_id", "incidents", ["assigned_to_user_id"])
    op.create_index("ix_incidents_due_at", "incidents", ["due_at"])
    op.create_table(
        "incident_events",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("incident_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(24), nullable=True),
        sa.Column("to_status", sa.String(24), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["org_id", "incident_id"],
            ["incidents.org_id", "incidents.id"],
            name="fk_incident_event_org_incident",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incident_events_org_id", "incident_events", ["org_id"])
    op.create_index("ix_incident_events_incident_id", "incident_events", ["incident_id"])


def downgrade() -> None:
    op.drop_index("ix_incident_events_incident_id", table_name="incident_events")
    op.drop_index("ix_incident_events_org_id", table_name="incident_events")
    op.drop_table("incident_events")
    op.drop_index("ix_incidents_due_at", table_name="incidents")
    op.drop_index("ix_incidents_assigned_to_user_id", table_name="incidents")
    op.drop_constraint("fk_incident_resolver", "incidents", type_="foreignkey")
    op.drop_constraint("fk_incident_assignee", "incidents", type_="foreignkey")
    op.drop_column("incidents", "reopened_count")
    op.drop_column("incidents", "resolved_at")
    op.drop_column("incidents", "resolved_by_user_id")
    op.drop_column("incidents", "due_at")
    op.drop_column("incidents", "action_plan")
    op.drop_column("incidents", "root_cause")
    op.drop_column("incidents", "assigned_to_user_id")
    op.drop_constraint("uq_incidents_org_id", "incidents", type_="unique")
