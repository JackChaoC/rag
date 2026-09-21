from __future__ import annotations

from rag.core.embedding.embedder import Embedder
from rag.core.embedding.text import document_embedding_text
from rag.infrastructure.database.entities.document import DocumentStatus
from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository
from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.infrastructure.messaging.models import IndexMessage, IndexOperation
from rag.infrastructure.vector_store.entities.vector_record import VectorRecord
from rag.infrastructure.vector_store.repositories.vector_repository import VectorRepository


class IndexingWorker:
    def __init__(
        self, documents: DocumentRepository, chunks: ChunkRepository,
        embedder: Embedder, vectors: VectorRepository,
    ) -> None:
        self._documents = documents
        self._chunks = chunks
        self._embedder = embedder
        self._vectors = vectors

    async def handle(self, message: IndexMessage) -> None:
        document = await self._documents.get(message.document_id)
        if document is None:
            raise LookupError("document not found")
        if message.version < document.current_version:
            stale = await self._chunks.for_version(document.id, message.version)
            await self._vectors.delete([chunk.id for chunk in stale])
            return
        if message.version > document.current_version:
            raise RuntimeError("message version is newer than the document")
        if message.operation is IndexOperation.DELETE:
            await self._delete(document.id)
            return
        if document.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
            raise RuntimeError("document is being deleted")
        claimed = await self._documents.set_status(
            document.id, DocumentStatus.INDEXING,
            expected={DocumentStatus.PENDING, DocumentStatus.FAILED, DocumentStatus.READY},
        )
        if not claimed:
            raise RuntimeError("document is already being indexed")
        try:
            target = await self._chunks.for_version(document.id, message.version)
            if not target:
                raise RuntimeError("document version has no chunks")
            embeddings = await self._embedder.embed([
                _embedding_text(document.title, chunk.content, chunk.metadata) for chunk in target
            ])
            dimension = len(embeddings[0])
            await self._vectors.ensure_collection(dimension)
            await self._vectors.upsert([
                VectorRecord(chunk.id, vector) for chunk, vector in zip(target, embeddings, strict=True)
            ])
            await self._documents.activate_version(document.id, message.version)
            old_ids = await self._chunks.all_ids(document.id, exclude_version=message.version)
            await self._vectors.delete(old_ids)
        except Exception as exc:
            await self._documents.set_status(
                document.id, DocumentStatus.FAILED, error=str(exc)[:4000],
                expected={DocumentStatus.INDEXING},
            )
            raise

    async def fail(self, message: IndexMessage, error: Exception) -> None:
        if message.operation is not IndexOperation.DELETE:
            target = await self._chunks.for_version(message.document_id, message.version)
            await self._vectors.delete([chunk.id for chunk in target])
        await self._documents.set_status(
            message.document_id, DocumentStatus.FAILED, error=str(error)[:4000],
        )

    async def _delete(self, document_id) -> None:
        ids = await self._chunks.all_ids(document_id)
        await self._vectors.delete(ids)
        await self._documents.mark_deleted(document_id)

    async def rebuild_all(self) -> int:
        count = 0
        for document in await self._documents.list():
            if document.status is not DocumentStatus.READY:
                continue
            chunks = await self._chunks.for_version(document.id, document.current_version)
            if not chunks:
                continue
            embeddings = await self._embedder.embed([
                _embedding_text(document.title, chunk.content, chunk.metadata) for chunk in chunks
            ])
            await self._vectors.ensure_collection(len(embeddings[0]))
            await self._vectors.upsert([
                VectorRecord(chunk.id, vector) for chunk, vector in zip(chunks, embeddings, strict=True)
            ])
            count += len(chunks)
        return count


def _embedding_text(title: str | None, content: str, metadata: dict) -> str:
    heading = metadata.get("heading")
    return document_embedding_text(
        content,
        document_title=title,
        section_heading=heading if isinstance(heading, str) else None,
    )
