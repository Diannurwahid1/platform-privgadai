"""Persist cited Tavily market evidence on each borrower estimate.

Revision ID: d1c9f4a7b216
Revises: a6b4e3d91c02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1c9f4a7b216"
down_revision: str | Sequence[str] | None = "a6b4e3d91c02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_appraisal_estimates", sa.Column("research_result", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))


def downgrade() -> None:
    op.drop_column("ai_appraisal_estimates", "research_result")
