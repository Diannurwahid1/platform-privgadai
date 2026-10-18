"""Borrower accounts, AI evidence and comparable-backed estimates.

Revision ID: a6b4e3d91c02
Revises: c4a7d9e2f531
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a6b4e3d91c02"
down_revision: str | Sequence[str] | None = "c4a7d9e2f531"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "borrower_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("borrower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone_ciphertext", sa.String(500), nullable=False),
        sa.Column("password_hash", sa.String(300), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id", "borrower_id"], ["borrowers.org_id", "borrowers.id"],
            name="fk_borrower_account_org_borrower", ondelete="CASCADE",
        ),
        sa.UniqueConstraint("org_id", "email", name="uq_borrower_account_org_email"),
        sa.UniqueConstraint("org_id", "borrower_id", name="uq_borrower_account_org_borrower"),
    )
    op.create_index("ix_borrower_accounts_org_id", "borrower_accounts", ["org_id"])
    op.create_index("ix_borrower_accounts_borrower_id", "borrower_accounts", ["borrower_id"])
    op.create_table(
        "borrower_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["borrower_accounts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_borrower_session_token_hash"),
    )
    op.create_index("ix_borrower_sessions_account_id", "borrower_sessions", ["account_id"])
    op.create_index("ix_borrower_sessions_expires_at", "borrower_sessions", ["expires_at"])
    op.create_table(
        "appraisal_comparables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_code", sa.String(40), nullable=False),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("model", sa.String(120), nullable=True),
        sa.Column("condition_grade", sa.String(24), nullable=False),
        sa.Column("market_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("source_label", sa.String(200), nullable=False),
        sa.Column("source_reference", sa.String(200), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("org_id", "id", name="uq_appraisal_comparable_org_id"),
    )
    op.create_index("ix_appraisal_comparables_org_id", "appraisal_comparables", ["org_id"])
    op.create_index("ix_appraisal_comparables_category_code", "appraisal_comparables", ["category_code"])
    op.create_table(
        "ai_appraisal_estimates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("borrower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category_code", sa.String(40), nullable=False),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("model", sa.String(120), nullable=True),
        sa.Column("condition_grade", sa.String(24), nullable=False),
        sa.Column("photo_sha256", sa.String(64), nullable=False),
        sa.Column("photo_key", sa.String(500), nullable=False),
        sa.Column("photo_content_type", sa.String(100), nullable=False),
        sa.Column("photo_file_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("quality_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("quality_findings", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("vision_result", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("vision_status", sa.String(24), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("estimator_version", sa.String(40), nullable=False),
        sa.Column("low_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("high_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("comparable_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comparable_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id", "borrower_id"], ["borrowers.org_id", "borrowers.id"],
            name="fk_ai_estimate_org_borrower", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "application_id"], ["loan_applications.org_id", "loan_applications.id"],
            name="fk_ai_estimate_org_application", ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("org_id", "id", name="uq_ai_appraisal_estimate_org_id"),
    )
    op.create_index("ix_ai_appraisal_estimates_org_id", "ai_appraisal_estimates", ["org_id"])
    op.create_index("ix_ai_appraisal_estimates_borrower_id", "ai_appraisal_estimates", ["borrower_id"])
    op.create_index("ix_ai_appraisal_estimates_application_id", "ai_appraisal_estimates", ["application_id"])
    op.add_column("offers", sa.Column("decision_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("offers", "decision_reason")
    op.drop_table("ai_appraisal_estimates")
    op.drop_table("appraisal_comparables")
    op.drop_table("borrower_sessions")
    op.drop_table("borrower_accounts")
