"""PrivGadai operations foundation.

Revision ID: a80d1c9f2b31
Revises: f1c64c1a8040
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a80d1c9f2b31"
down_revision: str | None = "f1c64c1a8040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column, sa.Column]:
    return (
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=24), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "code", name="uq_branches_org_code"),
        sa.UniqueConstraint("org_id", "id", name="uq_branches_org_id"),
    )
    op.create_index("ix_branches_org_id", "branches", ["org_id"])

    op.create_table(
        "borrowers",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("customer_reference", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=180), nullable=False),
        sa.Column("phone_masked", sa.String(length=32), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "customer_reference", name="uq_borrowers_org_reference"),
        sa.UniqueConstraint("org_id", "id", name="uq_borrowers_org_id"),
    )
    op.create_index("ix_borrowers_org_id", "borrowers", ["org_id"])

    op.create_table(
        "loan_applications",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("branch_id", sa.UUID(), nullable=False),
        sa.Column("borrower_id", sa.UUID(), nullable=False),
        sa.Column("assigned_user_id", sa.UUID(), nullable=True),
        sa.Column("application_no", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), server_default="normal", nullable=False),
        sa.Column("asset_category", sa.String(length=64), nullable=False),
        sa.Column("requested_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["org_id", "branch_id"],
            ["branches.org_id", "branches.id"],
            name="fk_applications_org_branch",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "borrower_id"],
            ["borrowers.org_id", "borrowers.id"],
            name="fk_applications_org_borrower",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "application_no", name="uq_applications_org_number"),
        sa.UniqueConstraint("org_id", "id", name="uq_applications_org_id"),
    )
    op.create_index("ix_loan_applications_org_id", "loan_applications", ["org_id"])
    op.create_index("ix_loan_applications_branch_id", "loan_applications", ["branch_id"])
    op.create_index("ix_loan_applications_borrower_id", "loan_applications", ["borrower_id"])
    op.create_index("ix_loan_applications_assigned_user_id", "loan_applications", ["assigned_user_id"])
    op.create_index("ix_loan_applications_status", "loan_applications", ["status"])
    op.create_index("ix_loan_applications_submitted_at", "loan_applications", ["submitted_at"])

    op.create_table(
        "assets",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("asset_code", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("condition_grade", sa.String(length=24), nullable=True),
        sa.Column("indicative_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("collateral_status", sa.String(length=32), server_default="with_customer", nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_assets_org_application",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "asset_code", name="uq_assets_org_code"),
        sa.UniqueConstraint("application_id", name="uq_assets_application"),
    )
    op.create_index("ix_assets_org_id", "assets", ["org_id"])
    op.create_index("ix_assets_application_id", "assets", ["application_id"])
    op.create_index("ix_assets_collateral_status", "assets", ["collateral_status"])

    op.create_table(
        "application_status_history",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["org_id", "application_id"],
            ["loan_applications.org_id", "loan_applications.id"],
            name="fk_history_org_application",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_application_status_history_org_id", "application_status_history", ["org_id"])
    op.create_index("ix_application_status_history_application_id", "application_status_history", ["application_id"])
    op.create_index("ix_application_status_history_created_at", "application_status_history", ["created_at"])


def downgrade() -> None:
    op.drop_table("application_status_history")
    op.drop_table("assets")
    op.drop_table("loan_applications")
    op.drop_table("borrowers")
    op.drop_table("branches")
