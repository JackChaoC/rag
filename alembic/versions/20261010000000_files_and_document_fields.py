"""Separate uploads from documents and replace source URI with file references."""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "20261010000000"
down_revision = "20260930000000"
branch_labels = None
depends_on = None


def upgrade():
    source_type = postgresql.ENUM(name="SourceType", create_type=False)
    team = postgresql.ENUM("wallet", "member", "devops", "data", "event", name="Team")
    team.create(op.get_bind(), checkfirst=True)
    op.create_table("files",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False, unique=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Keep legacy file locations and IDs so existing indexed chunks can link to files.
    op.execute("""INSERT INTO files (id, filename, file_path, source_type, content_hash, created_at)
        SELECT id, COALESCE(NULLIF(regexp_replace(source_uri, '^.*/', ''), ''),
                            regexp_replace(file_path, '^.*/', '')),
               file_path, source_type, content_hash, created_at FROM documents""")
    op.add_column("documents", sa.Column("file_id", sa.UUID(), nullable=True))
    op.execute("UPDATE documents SET file_id = id, title = COALESCE(NULLIF(btrim(title), ''), (SELECT filename FROM files WHERE files.id = documents.id))")
    op.alter_column("documents", "file_id", nullable=False)
    op.alter_column("documents", "title", nullable=False)
    op.create_foreign_key("documents_file_id_fkey", "documents", "files", ["file_id"], ["id"])
    op.create_index("ix_documents_file_id", "documents", ["file_id"])
    op.create_check_constraint("documents_title_not_blank", "documents", "length(btrim(title)) > 0")
    op.add_column("documents", sa.Column("team", postgresql.ENUM(name="Team", create_type=False), nullable=True))
    for name in ("project", "description", "operator"):
        op.add_column("documents", sa.Column(name, sa.Text(), nullable=True))
    op.drop_column("documents", "source_uri")


def downgrade():
    raise RuntimeError("Forward-only migration: restore a database backup to recover removed source URIs")
