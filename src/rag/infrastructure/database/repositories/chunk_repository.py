from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag.infrastructure.database.entities.chunk import Chunk
from rag.infrastructure.database.entities.document import DocumentStatus
from rag.infrastructure.database.models import ChunkRecord, DocumentRecord


@dataclass(frozen=True, slots=True)
class HydratedChunk:
    chunk_id: UUID
    document_id: UUID
    content: str
    source_uri: str
    title: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]


class ChunkRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def for_version(self, document_id: UUID, version: int) -> list[Chunk]:
        async with self._sessions() as session:
            records = await session.scalars(
                select(ChunkRecord)
                .where(
                    ChunkRecord.document_id == document_id,
                    ChunkRecord.version == version,
                )
                .order_by(ChunkRecord.chunk_index)
            )
            return [_chunk(record) for record in records]

    async def all_ids(self, document_id: UUID, *, exclude_version: int | None = None) -> list[UUID]:
        statement = select(ChunkRecord.id).where(ChunkRecord.document_id == document_id)
        if exclude_version is not None:
            statement = statement.where(ChunkRecord.version != exclude_version)
        async with self._sessions() as session:
            return list(await session.scalars(statement))

    async def get_for_document(self, document_id: UUID, chunk_id: UUID) -> HydratedChunk | None:
        found = await self.hydrate([chunk_id])
        item = found.get(chunk_id)
        return item if item and item.document_id == document_id else None

    async def hydrate(self, ids: Sequence[UUID]) -> dict[UUID, HydratedChunk]:
        if not ids:
            return {}
        statement = (
            select(
                ChunkRecord.id.label("chunk_id"),
                ChunkRecord.document_id,
                ChunkRecord.content,
                ChunkRecord.start_line,
                ChunkRecord.end_line,
                ChunkRecord.metadata_json,
                DocumentRecord.source_uri,
                DocumentRecord.title,
            )
            .join(DocumentRecord, DocumentRecord.id == ChunkRecord.document_id)
            .where(
                ChunkRecord.id.in_(ids),
                ChunkRecord.active.is_(True),
                DocumentRecord.status == DocumentStatus.READY,
                ChunkRecord.version == DocumentRecord.current_version,
            )
        )
        async with self._sessions() as session:
            rows = (await session.execute(statement)).all()
        return {
            row.chunk_id: HydratedChunk(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                content=row.content,
                source_uri=row.source_uri,
                title=row.title,
                start_line=row.start_line,
                end_line=row.end_line,
                metadata=dict(row.metadata_json),
            )
            for row in rows
        }


def _chunk(record: ChunkRecord) -> Chunk:
    return Chunk(
        id=record.id,
        document_id=record.document_id,
        version=record.version,
        chunk_index=record.chunk_index,
        content=record.content,
        start_line=record.start_line,
        end_line=record.end_line,
        token_count=record.token_count,
        metadata=dict(record.metadata_json),
        active=record.active,
        created_at=record.created_at,
    )
