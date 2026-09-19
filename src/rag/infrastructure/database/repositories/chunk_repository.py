from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg_pool import AsyncConnectionPool

from rag.infrastructure.database.entities.chunk import Chunk


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
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def for_version(self, document_id: UUID, version: int) -> list[Chunk]:
        async with self._pool.connection() as connection:
            rows = await (await connection.execute(
                'SELECT * FROM "chunks" WHERE document_id=%s AND version=%s ORDER BY chunk_index',
                (document_id, version),
            )).fetchall()
        return [_chunk(row) for row in rows]

    async def all_ids(self, document_id: UUID, *, exclude_version: int | None = None) -> list[UUID]:
        if exclude_version is None:
            query, params = 'SELECT id FROM "chunks" WHERE document_id=%s', (document_id,)
        else:
            query, params = 'SELECT id FROM "chunks" WHERE document_id=%s AND version<>%s', (document_id, exclude_version)
        async with self._pool.connection() as connection:
            rows = await (await connection.execute(query, params)).fetchall()
        return [row["id"] for row in rows]

    async def get_for_document(self, document_id: UUID, chunk_id: UUID) -> HydratedChunk | None:
        found = await self.hydrate([chunk_id])
        item = found.get(chunk_id)
        return item if item and item.document_id == document_id else None

    async def hydrate(self, ids: Sequence[UUID]) -> dict[UUID, HydratedChunk]:
        if not ids:
            return {}
        async with self._pool.connection() as connection:
            rows = await (await connection.execute(
            '''SELECT c.id, c.document_id, c.content, c.start_line, c.end_line, c.metadata,
                      d.source_uri, d.title
               FROM "chunks" c JOIN "documents" d ON d.id=c.document_id
               WHERE c.id = ANY(%s::uuid[]) AND c.active=TRUE AND d.status='ready'
                 AND c.version=d.current_version''', (list(ids),),
            )).fetchall()
        result: dict[UUID, HydratedChunk] = {}
        for row in rows:
            metadata = row["metadata"]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            result[row["id"]] = HydratedChunk(
                row["id"], row["document_id"], row["content"], row["source_uri"], row["title"],
                row["start_line"], row["end_line"], metadata,
            )
        return result


def _chunk(row: dict) -> Chunk:
    metadata = row["metadata"]
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    return Chunk(
        id=row["id"], document_id=row["document_id"], version=row["version"],
        chunk_index=row["chunk_index"], content=row["content"], start_line=row["start_line"],
        end_line=row["end_line"], token_count=row["token_count"], metadata=metadata,
        active=row["active"], created_at=row["created_at"],
    )
