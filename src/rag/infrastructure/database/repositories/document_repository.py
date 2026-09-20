from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag.infrastructure.database.entities.chunk import Chunk
from rag.infrastructure.database.entities.document import Document, DocumentStatus
from rag.infrastructure.database.models import ChunkRecord, DocumentRecord


class DocumentRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def get(self, document_id: UUID) -> Document | None:
        async with self._sessions() as session:
            record = await session.get(DocumentRecord, document_id)
        return _document(record) if record else None

    async def get_by_source_uri(self, source_uri: str) -> Document | None:
        async with self._sessions() as session:
            record = await session.scalar(
                select(DocumentRecord).where(DocumentRecord.source_uri == source_uri)
            )
        return _document(record) if record else None

    async def list(self) -> list[Document]:
        async with self._sessions() as session:
            records = await session.scalars(
                select(DocumentRecord).order_by(DocumentRecord.created_at, DocumentRecord.id)
            )
            return [_document(record) for record in records]

    async def create_with_chunks(self, document: Document, chunks: Sequence[Chunk]) -> None:
        _require_chunks(chunks)
        async with self._sessions.begin() as session:
            session.add(_document_record(document))
            await session.flush()
            session.add_all(_chunk_record(chunk) for chunk in chunks)

    async def add_version(self, document: Document, chunks: Sequence[Chunk]) -> None:
        _require_chunks(chunks)
        async with self._sessions.begin() as session:
            result = await session.execute(
                update(DocumentRecord)
                .where(
                    DocumentRecord.id == document.id,
                    DocumentRecord.status.not_in(
                        [DocumentStatus.DELETING, DocumentStatus.DELETED]
                    ),
                )
                .values(
                    content=document.content,
                    content_hash=document.content_hash,
                    current_version=document.current_version,
                    status=DocumentStatus.PENDING,
                    last_error=None,
                    updated_at=func.current_timestamp(),
                )
            )
            if result.rowcount != 1:
                raise RuntimeError("document cannot be reindexed in its current state")
            session.add_all(_chunk_record(chunk) for chunk in chunks)

    async def set_status(
        self, document_id: UUID, status: DocumentStatus, *, error: str | None = None,
        expected: set[DocumentStatus] | None = None,
    ) -> bool:
        conditions = [DocumentRecord.id == document_id]
        if expected:
            conditions.append(DocumentRecord.status.in_(expected))
        async with self._sessions.begin() as session:
            result = await session.execute(
                update(DocumentRecord)
                .where(*conditions)
                .values(
                    status=status,
                    last_error=error,
                    updated_at=func.current_timestamp(),
                )
            )
            return result.rowcount == 1

    async def activate_version(self, document_id: UUID, version: int) -> None:
        async with self._sessions.begin() as session:
            current_version = await session.scalar(
                select(DocumentRecord.current_version)
                .where(DocumentRecord.id == document_id)
                .with_for_update()
            )
            if current_version != version:
                raise RuntimeError("document version changed while indexing")
            await session.execute(
                update(ChunkRecord)
                .where(ChunkRecord.document_id == document_id)
                .values(active=ChunkRecord.version == version)
            )
            await session.execute(
                update(DocumentRecord)
                .where(DocumentRecord.id == document_id)
                .values(
                    status=DocumentStatus.READY,
                    last_error=None,
                    updated_at=func.current_timestamp(),
                )
            )

    async def mark_deleted(self, document_id: UUID) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(ChunkRecord)
                .where(ChunkRecord.document_id == document_id)
                .values(active=False)
            )
            await session.execute(
                update(DocumentRecord)
                .where(DocumentRecord.id == document_id)
                .values(
                    status=DocumentStatus.DELETED,
                    last_error=None,
                    updated_at=func.current_timestamp(),
                )
            )


def _require_chunks(chunks: Sequence[Chunk]) -> None:
    if not chunks:
        raise ValueError("a document version must contain at least one chunk")


def _document_record(document: Document) -> DocumentRecord:
    return DocumentRecord(
        id=document.id,
        source_uri=document.source_uri,
        title=document.title,
        source_type=document.source_type,
        content=document.content,
        content_hash=document.content_hash,
        current_version=document.current_version,
        status=document.status,
        last_error=document.last_error,
        metadata_json=document.metadata,
    )


def _chunk_record(chunk: Chunk) -> ChunkRecord:
    return ChunkRecord(
        id=chunk.id,
        document_id=chunk.document_id,
        version=chunk.version,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        token_count=chunk.token_count,
        metadata_json=chunk.metadata,
        active=chunk.active,
    )


def _document(record: DocumentRecord) -> Document:
    return Document(
        id=record.id,
        source_uri=record.source_uri,
        title=record.title,
        source_type=record.source_type,
        content=record.content,
        content_hash=record.content_hash,
        current_version=record.current_version,
        status=record.status,
        last_error=record.last_error,
        metadata=dict(record.metadata_json),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
