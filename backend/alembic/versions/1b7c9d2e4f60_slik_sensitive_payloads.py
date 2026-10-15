"""Encrypted KYC and SLIK sensitive payloads.

Revision ID: 1b7c9d2e4f60
Revises: 0a9e7c24d801
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1b7c9d2e4f60"
down_revision: str | None = "0a9e7c24d801"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("kyc_verifications", sa.Column("national_id_ciphertext", sa.Text(), nullable=True))
    op.add_column("regulatory_report_runs", sa.Column("sensitive_payload_ciphertext", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("regulatory_report_runs", "sensitive_payload_ciphertext")
    op.drop_column("kyc_verifications", "national_id_ciphertext")
