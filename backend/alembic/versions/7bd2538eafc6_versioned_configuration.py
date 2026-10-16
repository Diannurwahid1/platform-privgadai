"""Versioned effective-dated configuration workbench.

Revision ID: 7bd2538eafc6
Revises: 6ac1427d9eb5
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7bd2538eafc6"
down_revision: str | None = "6ac1427d9eb5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "configuration_versions",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("domain", sa.String(32), nullable=False),
        sa.Column("config_key", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), server_default="draft", nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("approved_by_user_id", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supersedes_id"], ["configuration_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "domain", "config_key", "version", name="uq_configuration_version"),
        sa.UniqueConstraint("org_id", "id", name="uq_configuration_org_id"),
    )
    for column in ("org_id", "domain", "config_key", "status", "effective_from"):
        op.create_index(f"ix_configuration_versions_{column}", "configuration_versions", [column])
    op.create_index(
        "uq_configuration_effective_key",
        "configuration_versions",
        ["org_id", "domain", "config_key"],
        unique=True,
        postgresql_where=sa.text("status = 'effective'"),
    )
    op.create_table(
        "configuration_events",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("configuration_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(24), nullable=True),
        sa.Column("to_status", sa.String(24), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["org_id", "configuration_id"],
            ["configuration_versions.org_id", "configuration_versions.id"],
            name="fk_configuration_event_org_version",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_configuration_events_org_id", "configuration_events", ["org_id"])
    op.create_index("ix_configuration_events_configuration_id", "configuration_events", ["configuration_id"])


def downgrade() -> None:
    op.drop_index("ix_configuration_events_configuration_id", table_name="configuration_events")
    op.drop_index("ix_configuration_events_org_id", table_name="configuration_events")
    op.drop_table("configuration_events")
    op.drop_index("uq_configuration_effective_key", table_name="configuration_versions")
    for column in reversed(("org_id", "domain", "config_key", "status", "effective_from")):
        op.drop_index(f"ix_configuration_versions_{column}", table_name="configuration_versions")
    op.drop_table("configuration_versions")
