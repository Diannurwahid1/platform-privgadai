"""Customer KYC workflow.

Revision ID: b31f0a2c7d11
Revises: d5f1834b72a1
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b31f0a2c7d11"
down_revision: str | None = "d5f1834b72a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kyc_verifications",
        sa.Column("org_id", sa.UUID(), nullable=False), sa.Column("borrower_id", sa.UUID(), nullable=False),
        sa.Column("initiated_by_user_id", sa.UUID(), nullable=False), sa.Column("reviewed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("document_type", sa.String(24), server_default="ktp", nullable=False),
        sa.Column("nik_fingerprint", sa.String(64), nullable=False), sa.Column("national_id_masked", sa.String(32), nullable=False),
        sa.Column("legal_name", sa.String(180), nullable=False), sa.Column("birth_place", sa.String(100), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False), sa.Column("gender", sa.String(16), nullable=False),
        sa.Column("address", sa.Text(), nullable=False), sa.Column("province", sa.String(100), nullable=False),
        sa.Column("city", sa.String(100), nullable=False), sa.Column("occupation", sa.String(120), nullable=True),
        sa.Column("nationality", sa.String(3), server_default="IDN", nullable=False),
        sa.Column("verification_method", sa.String(32), server_default="manual_branch", nullable=False),
        sa.Column("provider_name", sa.String(80), nullable=True), sa.Column("provider_reference", sa.String(120), nullable=True),
        sa.Column("status", sa.String(24), server_default="pending_documents", nullable=False),
        sa.Column("risk_level", sa.String(16), server_default="standard", nullable=False),
        sa.Column("face_match_score", sa.Numeric(5, 2), nullable=True), sa.Column("liveness_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("document_authenticity_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("pep_match", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("sanctions_match", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=True), sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True), sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id", "borrower_id"], ["borrowers.org_id", "borrowers.id"], name="fk_kyc_verification_org_borrower", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("org_id", "id", name="uq_kyc_verifications_org_id"),
    )
    for column in ("org_id", "borrower_id", "nik_fingerprint", "status"):
        op.create_index(f"ix_kyc_verifications_{column}", "kyc_verifications", [column])
    op.create_table(
        "kyc_documents",
        sa.Column("org_id", sa.UUID(), nullable=False), sa.Column("verification_id", sa.UUID(), nullable=False),
        sa.Column("document_side", sa.String(24), nullable=False), sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("object_key", sa.String(500), nullable=False), sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False), sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("encryption_version", sa.String(16), server_default="fernet-v1", nullable=False),
        sa.Column("scan_status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id", "verification_id"], ["kyc_verifications.org_id", "kyc_verifications.id"], name="fk_kyc_document_org_verification", ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kyc_documents_org_id", "kyc_documents", ["org_id"]); op.create_index("ix_kyc_documents_verification_id", "kyc_documents", ["verification_id"])
    op.create_table(
        "kyc_events",
        sa.Column("org_id", sa.UUID(), nullable=False), sa.Column("verification_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True), sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(24), nullable=True), sa.Column("to_status", sa.String(24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True), sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id", "verification_id"], ["kyc_verifications.org_id", "kyc_verifications.id"], name="fk_kyc_event_org_verification", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kyc_events_org_id", "kyc_events", ["org_id"]); op.create_index("ix_kyc_events_verification_id", "kyc_events", ["verification_id"]); op.create_index("ix_kyc_events_occurred_at", "kyc_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("kyc_events")
    op.drop_table("kyc_documents")
    op.drop_table("kyc_verifications")
