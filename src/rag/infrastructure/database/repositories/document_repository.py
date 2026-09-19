from __future__ import annotations

import json
from collections.abc import Sequence
from uuid import UUID

from psycopg_pool import AsyncConnectionPool

from rag.infrastructure.database.entities.chunk import Chunk
from rag.infrastructure.database.entities.document import Document, DocumentStatus, SourceType


class DocumentRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def get(self, document_id: UUID) -> Document | None:
        async with self._pool.connection() as connection:
            cursor = await connection.execute('SELECT * FROM "documents" WHERE id = %s', (document_id,))
            row = await cursor.fetchone()
        return _document(row) if row else None

    async def get_by_source_uri(self, source_uri: str) -> Document | None:
        async with self._pool.connection() as connection:
            cursor = await connection.execute('SELECT * FROM "documents" WHERE source_uri = %s', (source_uri,))
            row = await cursor.fetchone()
        return _document(row) if row else None

    async def list(self) -> list[Document]:
        async with self._pool.connection() as connection:
            rows = await (await connection.execute('SELECT * FROM "documents" ORDER BY created_at, id')).fetchall()
        return [_document(row) for row in rows]

    async def create_with_chunks(self, document: Document, chunks: Sequence[Chunk]) -> None:
        async with self._pool.connection() as connection, connection.transaction():
            await connection.execute(
                '''INSERT INTO "documents"
                   (id, source_uri, title, source_type, content, content_hash, current_version, status, last_error, metadata)
                   VALUES (%s,%s,%s,%s::"SourceType",%s,%s,%s,%s::"DocumentStatus",%s,%s::jsonb)''',
                (document.id, document.source_uri, document.title, document.source_type.value,
                document.content, document.content_hash, document.current_version,
                document.status.value, document.last_error, json.dumps(document.metadata)),
            )
            await _insert_chunks(connection, chunks)

    async def add_version(self, document: Document, chunks: Sequence[Chunk]) -> None:
        async with self._pool.connection() as connection, connection.transaction():
            result = await connection.execute(
                '''UPDATE "documents" SET content=%s, content_hash=%s, current_version=%s,
                   status='pending', last_error=NULL, updated_at=CURRENT_TIMESTAMP
                   WHERE id=%s AND status NOT IN ('deleting','deleted')''',
                (document.content, document.content_hash, document.current_version, document.id),
            )
            if result.rowcount != 1:
                raise RuntimeError("document cannot be reindexed in its current state")
            await _insert_chunks(connection, chunks)

    async def set_status(
        self, document_id: UUID, status: DocumentStatus, *, error: str | None = None,
        expected: set[DocumentStatus] | None = None,
    ) -> bool:
        args: list[object] = [status.value, error, document_id]
        where = "id=%s"
        if expected:
            values = tuple(item.value for item in expected)
            where += " AND status::text = ANY(%s)"
            args.append(list(values))
        async with self._pool.connection() as connection:
            result = await connection.execute(
                f'''UPDATE "documents" SET status=%s::"DocumentStatus", last_error=%s,
                    updated_at=CURRENT_TIMESTAMP WHERE {where}''', args,
            )
            return result.rowcount == 1

    async def activate_version(self, document_id: UUID, version: int) -> None:
        async with self._pool.connection() as connection, connection.transaction():
            row = await (await connection.execute(
                'SELECT current_version FROM "documents" WHERE id=%s FOR UPDATE', (document_id,),
            )).fetchone()
            if row is None or row["current_version"] != version:
                raise RuntimeError("document version changed while indexing")
            await connection.execute(
                'UPDATE "chunks" SET active = (version=%s) WHERE document_id=%s', (version, document_id),
            )
            await connection.execute(
                '''UPDATE "documents" SET status='ready', last_error=NULL, updated_at=CURRENT_TIMESTAMP
                   WHERE id=%s''', (document_id,),
            )

    async def mark_deleted(self, document_id: UUID) -> None:
        async with self._pool.connection() as connection, connection.transaction():
            await connection.execute('UPDATE "chunks" SET active=FALSE WHERE document_id=%s', (document_id,))
            await connection.execute(
                '''UPDATE "documents" SET status='deleted', last_error=NULL, updated_at=CURRENT_TIMESTAMP
                   WHERE id=%s''', (document_id,),
            )


async def _insert_chunks(connection, chunks: Sequence[Chunk]) -> None:
    if not chunks:
        raise ValueError("a document version must contain at least one chunk")
    cursor = connection.cursor()
    await cursor.executemany(
        '''INSERT INTO "chunks"
           (id, document_id, version, chunk_index, content, start_line, end_line, token_count, metadata, active)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)''',
        [
            (chunk.id, chunk.document_id, chunk.version, chunk.chunk_index, chunk.content,
             chunk.start_line, chunk.end_line, chunk.token_count, json.dumps(chunk.metadata), chunk.active)
            for chunk in chunks
        ],
    )


def _document(row: dict) -> Document:
    metadata = row["metadata"]
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    return Document(
        id=row["id"], source_uri=row["source_uri"], title=row["title"],
        source_type=SourceType(row["source_type"]), content=row["content"],
        content_hash=row["content_hash"], current_version=row["current_version"],
        status=DocumentStatus(row["status"]), last_error=row["last_error"], metadata=metadata,
        created_at=row["created_at"], updated_at=row["updated_at"],
    )
