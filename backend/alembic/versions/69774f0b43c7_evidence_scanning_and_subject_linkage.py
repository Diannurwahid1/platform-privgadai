"""evidence scanning and subject linkage

Revision ID: 69774f0b43c7
Revises: 82dcf7fa8aa0
Create Date: 2026-10-16 13:25:37.928805

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "69774f0b43c7"
down_revision: str | None = "82dcf7fa8aa0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "evidence_files", sa.Column("subject_type", sa.String(length=32), server_default="application", nullable=False)
    )
    op.add_column("evidence_files", sa.Column("subject_id", sa.UUID(), nullable=True))
    op.execute("UPDATE evidence_files SET subject_id = application_id WHERE subject_id IS NULL")
    op.alter_column("evidence_files", "subject_id", existing_type=sa.UUID(), nullable=False)
    op.add_column("evidence_files", sa.Column("uploaded_by_user_id", sa.UUID(), nullable=True))
    op.add_column("evidence_files", sa.Column("scanner_engine", sa.String(length=64), nullable=True))
    op.add_column("evidence_files", sa.Column("scan_detail", sa.String(length=500), nullable=True))
    op.add_column("evidence_files", sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("evidence_files", sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_evidence_files_subject_id", "evidence_files", ["subject_id"])
    op.create_unique_constraint("uq_evidence_files_org_id", "evidence_files", ["org_id", "id"])
    op.create_foreign_key(
        "fk_evidence_files_uploader", "evidence_files", "users", ["uploaded_by_user_id"], ["id"], ondelete="SET NULL"
    )
    op.create_table(
        "evidence_events",
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("evidence_file_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("from_status", sa.String(length=24), nullable=True),
        sa.Column("to_status", sa.String(length=24), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["org_id", "evidence_file_id"],
            ["evidence_files.org_id", "evidence_files.id"],
            name="fk_evidence_event_org_file",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_events_evidence_file_id", "evidence_events", ["evidence_file_id"])
    op.create_index("ix_evidence_events_org_id", "evidence_events", ["org_id"])
    op.add_column("kyc_documents", sa.Column("scanner_engine", sa.String(length=64), nullable=True))
    op.add_column("kyc_documents", sa.Column("scan_detail", sa.String(length=500), nullable=True))
    op.add_column("kyc_documents", sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("kyc_documents", sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("kyc_documents", "quarantined_at")
    op.drop_column("kyc_documents", "scanned_at")
    op.drop_column("kyc_documents", "scan_detail")
    op.drop_column("kyc_documents", "scanner_engine")
    op.drop_index("ix_evidence_events_org_id", table_name="evidence_events")
    op.drop_index("ix_evidence_events_evidence_file_id", table_name="evidence_events")
    op.drop_table("evidence_events")
    op.drop_constraint("fk_evidence_files_uploader", "evidence_files", type_="foreignkey")
    op.drop_constraint("uq_evidence_files_org_id", "evidence_files", type_="unique")
    op.drop_index("ix_evidence_files_subject_id", table_name="evidence_files")
    op.drop_column("evidence_files", "quarantined_at")
    op.drop_column("evidence_files", "scanned_at")
    op.drop_column("evidence_files", "scan_detail")
    op.drop_column("evidence_files", "scanner_engine")
    op.drop_column("evidence_files", "uploaded_by_user_id")
    op.drop_column("evidence_files", "subject_id")
    op.drop_column("evidence_files", "subject_type")
