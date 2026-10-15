"""Drop JSON defaults for product rule columns.

Revision ID: d5f1834b72a1
Revises: 9b860853fd6e
Create Date: 2026-10-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d5f1834b72a1"
down_revision: str | None = "9b860853fd6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("loan_products", "fee_rules", server_default=None)
    op.alter_column("loan_products", "approval_policy", server_default=None)


def downgrade() -> None:
    op.alter_column("loan_products", "fee_rules", server_default="{}")
    op.alter_column("loan_products", "approval_policy", server_default="{}")
