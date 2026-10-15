"""Allow organization-wide approval requests.

Revision ID: d53b21a93f31
Revises: c42a10f82e20
Create Date: 2026-10-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d53b21a93f31"
down_revision: str | None = "c42a10f82e20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("approval_requests", "branch_id", nullable=True)


def downgrade() -> None:
    op.alter_column("approval_requests", "branch_id", nullable=False)
