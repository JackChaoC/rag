from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Integer,
    BigInteger,
    ForeignKey,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from rag.services.documents.types.document import DocumentStatus, SourceType, Team


def _enum_values(enum_type) -> list[str]:
    return [item.value for item in enum_type]


source_type_enum = Enum(SourceType, name="SourceType", values_callable=_enum_values)
document_status_enum = Enum(
    DocumentStatus,
    name="DocumentStatus",
    values_callable=_enum_values,
)


class Base(DeclarativeBase):
    pass


class FileRecord(Base):
    __tablename__ = "files"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    filename: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(Text, unique=True)
    source_type: Mapped[SourceType] = mapped_column(source_type_enum)
    content_hash: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp())


class DocumentRecord(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("length(btrim(title)) > 0", name="documents_title_not_blank"),
        CheckConstraint("current_version >= 1", name="documents_current_version_check"),
        CheckConstraint(
            "jsonb_typeof(metadata) = 'object'", name="documents_metadata_object"
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    file_id: Mapped[UUID] = mapped_column(ForeignKey("files.id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    team: Mapped[Team | None] = mapped_column(Enum(Team, name="Team", values_callable=_enum_values))
    project: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    operator: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[SourceType] = mapped_column(source_type_enum)
    file_path: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(Text)
    current_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    status: Mapped[DocumentStatus] = mapped_column(document_status_enum)
    last_error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
