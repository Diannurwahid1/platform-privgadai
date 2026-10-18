"""Allow borrower-initiated KYC without impersonating a staff maker.

Revision ID: f36a91c82d70
Revises: e2f7b4a91c60
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f36a91c82d70"
down_revision: str | Sequence[str] | None = "e2f7b4a91c60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("kyc_verifications", "initiated_by_user_id", nullable=True)


def downgrade() -> None:
    op.alter_column("kyc_verifications", "initiated_by_user_id", nullable=False)
