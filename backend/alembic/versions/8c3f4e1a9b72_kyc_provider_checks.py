"""Store encrypted OCR and identity-provider evidence.

Revision ID: 8c3f4e1a9b72
Revises: 14ba7eb88c58
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8c3f4e1a9b72"
down_revision: str | None = "14ba7eb88c58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kyc_provider_checks",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("verification_id", sa.UUID(), nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=False),
        sa.Column("check_type", sa.String(length=32), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=False),
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider_reference", sa.String(length=160), nullable=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("response_ciphertext", sa.Text(), nullable=False),
        sa.Column("officially_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["org_id", "verification_id"],
            ["kyc_verifications.org_id", "kyc_verifications.id"],
            name="fk_kyc_provider_check_org_verification",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kyc_provider_checks_org_id", "kyc_provider_checks", ["org_id"])
    op.create_index("ix_kyc_provider_checks_verification_id", "kyc_provider_checks", ["verification_id"])


def downgrade() -> None:
    op.drop_index("ix_kyc_provider_checks_verification_id", table_name="kyc_provider_checks")
    op.drop_index("ix_kyc_provider_checks_org_id", table_name="kyc_provider_checks")
    op.drop_table("kyc_provider_checks")
