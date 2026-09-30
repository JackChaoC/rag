"""Use stored files and Qdrant Nodes; intentionally requires an empty document store.

Revision ID: 20260930000000
Revises: 20260920000000
"""

import sqlalchemy as sa

from alembic import op

revision = "20260930000000"
down_revision = "20260920000000"
branch_labels = None
depends_on = None


def upgrade():
    # No conversion or deletion of existing data is authorized for this branch.
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM documents)")):
        raise RuntimeError(
            "llama-index requires a NEW empty database; existing documents will not be migrated"
        )
    op.drop_table("chunks")
    op.drop_column("documents", "content")
    op.add_column("documents", sa.Column("file_path", sa.Text(), nullable=False))


def downgrade():
    raise RuntimeError(
        "Forward-only migration; use a new database for the previous application"
    )
