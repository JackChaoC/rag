from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from rag.infrastructure.database.entities.document import DocumentStatus, SourceType


def _enum_values(enum_type) -> list[str]:
    return [item.value for item in enum_type]


source_type_enum = Enum(SourceType, name="SourceType", values_callable=_enum_values)
document_status_enum = Enum(
    DocumentStatus, name="DocumentStatus", values_callable=_enum_values,
)


class Base(DeclarativeBase):
    pass


class DocumentRecord(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("current_version >= 1", name="documents_current_version_check"),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="documents_metadata_object"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    source_uri: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[SourceType] = mapped_column(source_type_enum)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(Text)
    current_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    status: Mapped[DocumentStatus] = mapped_column(document_status_enum)
    last_error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class ChunkRecord(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        CheckConstraint("version >= 1", name="chunks_version_check"),
        CheckConstraint("chunk_index >= 0", name="chunks_chunk_index_check"),
        CheckConstraint("start_line IS NULL OR start_line >= 1", name="chunks_start_line_check"),
        CheckConstraint("end_line IS NULL OR end_line >= 1", name="chunks_end_line_check"),
        CheckConstraint("token_count IS NULL OR token_count >= 0", name="chunks_token_count_check"),
        CheckConstraint(
            "start_line IS NULL OR end_line IS NULL OR start_line <= end_line",
            name="chunks_line_range",
        ),
        CheckConstraint("jsonb_typeof(metadata) = 'object'", name="chunks_metadata_object"),
        UniqueConstraint(
            "document_id", "version", "chunk_index",
            name="chunks_document_id_version_chunk_index_key",
        ),
        Index("chunks_document_id_active_idx", "document_id", "active"),
        Index("chunks_document_id_version_idx", "document_id", "version"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    document_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
    )
    version: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    token_count: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"),
    )
    active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(),
    )
