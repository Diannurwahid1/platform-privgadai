"""rename provider verification flag for internal OCR semantics

Revision ID: c4a7d9e2f531
Revises: 8c3f4e1a9b72
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c4a7d9e2f531"
down_revision: str | Sequence[str] | None = "8c3f4e1a9b72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("kyc_provider_checks", "officially_verified", new_column_name="internal_verified")


def downgrade() -> None:
    op.alter_column("kyc_provider_checks", "internal_verified", new_column_name="officially_verified")

