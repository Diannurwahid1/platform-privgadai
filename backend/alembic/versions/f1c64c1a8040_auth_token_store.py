"""Auth token store for PostgreSQL-only deployments.

Revision ID: f1c64c1a8040
Revises: d5ae679a86c1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f1c64c1a8040"
down_revision: str | None = "d5ae679a86c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_token_store",
        sa.Column("key_hash", sa.String(length=64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_token_store_expires_at", "auth_token_store", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_auth_token_store_expires_at", table_name="auth_token_store")
    op.drop_table("auth_token_store")
