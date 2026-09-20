"""Create the initial document and chunk schema.

Revision ID: 20260920000000
Revises:
Create Date: 2026-09-20 00:00:00
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260920000000"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


source_type = postgresql.ENUM(
    "markdown", "text", "pdf", "word", "excel", "powerpoint", "html",
    name="SourceType", create_type=False,
)
document_status = postgresql.ENUM(
    "pending", "indexing", "ready", "failed", "deleting", "deleted",
    name="DocumentStatus", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    source_type.create(bind, checkfirst=False)
    document_status.create(bind, checkfirst=False)
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("current_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", document_status, nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"), nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.CheckConstraint(
            "current_version >= 1", name="documents_current_version_check",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'", name="documents_metadata_object",
        ),
        sa.PrimaryKeyConstraint("id", name="documents_pkey"),
        sa.UniqueConstraint("source_uri", name="documents_source_uri_key"),
    )
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("end_line", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"), nullable=False,
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False,
        ),
        sa.CheckConstraint("version >= 1", name="chunks_version_check"),
        sa.CheckConstraint("chunk_index >= 0", name="chunks_chunk_index_check"),
        sa.CheckConstraint(
            "start_line IS NULL OR start_line >= 1", name="chunks_start_line_check",
        ),
        sa.CheckConstraint(
            "end_line IS NULL OR end_line >= 1", name="chunks_end_line_check",
        ),
        sa.CheckConstraint(
            "token_count IS NULL OR token_count >= 0", name="chunks_token_count_check",
        ),
        sa.CheckConstraint(
            "start_line IS NULL OR end_line IS NULL OR start_line <= end_line",
            name="chunks_line_range",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'", name="chunks_metadata_object",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"],
            name="chunks_document_id_fkey", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="chunks_pkey"),
        sa.UniqueConstraint(
            "document_id", "version", "chunk_index",
            name="chunks_document_id_version_chunk_index_key",
        ),
    )
    op.create_index(
        "chunks_document_id_active_idx", "chunks", ["document_id", "active"], unique=False,
    )
    op.create_index(
        "chunks_document_id_version_idx", "chunks", ["document_id", "version"], unique=False,
    )


def downgrade() -> None:
    op.drop_index("chunks_document_id_version_idx", table_name="chunks")
    op.drop_index("chunks_document_id_active_idx", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("documents")
    bind = op.get_bind()
    document_status.drop(bind, checkfirst=False)
    source_type.drop(bind, checkfirst=False)
