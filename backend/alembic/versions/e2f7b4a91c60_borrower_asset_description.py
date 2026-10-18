"""Store borrower-provided asset context for AI and human appraisal.

Revision ID: e2f7b4a91c60
Revises: d1c9f4a7b216
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e2f7b4a91c60"
down_revision: str | Sequence[str] | None = "d1c9f4a7b216"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_appraisal_estimates", sa.Column("asset_description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_appraisal_estimates", "asset_description")
