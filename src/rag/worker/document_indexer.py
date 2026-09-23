from __future__ import annotations

from rag.core.embedding.embedder import Embedder
from rag.core.embedding.text import document_embedding_text
from rag.infrastructure.database.entities.document import DocumentStatus
from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository
from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.infrastructure.messaging.models import IndexMessage
from rag.infrastructure.vector_store.entities.vector_record import VectorRecord
from rag.infrastructure.vector_store.repositories.vector_repository import VectorRepository


class DocumentIndexer:
    def __init__(
        self,
        documents: DocumentRepository,
        chunks: ChunkRepository,
        embedder: Embedder,
        vectors: VectorRepository,
    ) -> None:
        self._documents = documents
        self._chunks = chunks
        self._embedder = embedder
        self._vectors = vectors

    async def index(self, message: IndexMessage) -> None:
        document = await self._documents.get(message.document_id)
        if document is None:
            raise LookupError("document not found")
        if message.version < document.current_version:
            stale = await self._chunks.for_version(document.id, message.version)
            await self._vectors.delete([chunk.id for chunk in stale])
            return
        if message.version > document.current_version:
            raise RuntimeError("message version is newer than the document")
        if document.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
            raise RuntimeError("document is being deleted")

        claimed = await self._documents.set_status(
            document.id,
            DocumentStatus.INDEXING,
            expected={
                DocumentStatus.PENDING,
                DocumentStatus.FAILED,
                DocumentStatus.READY,
            },
        )
        if not claimed:
            raise RuntimeError("document is already being indexed")

        target = await self._chunks.for_version(document.id, message.version)
        if not target:
            raise RuntimeError("document version has no chunks")

        embeddings = await self._embedder.embed([
            document_embedding_text(
                chunk.content,
                document_title=document.title,
                section_heading=(
                    chunk.metadata.get("heading")
                    if isinstance(chunk.metadata.get("heading"), str)
                    else None
                ),
            )
            for chunk in target
        ])
        await self._vectors.ensure_collection(len(embeddings[0]))
        await self._vectors.upsert([
            VectorRecord(chunk.id, vector)
            for chunk, vector in zip(target, embeddings, strict=True)
        ])
        await self._documents.activate_version(document.id, message.version)
        old_ids = await self._chunks.all_ids(
            document.id,
            exclude_version=message.version,
        )
        await self._vectors.delete(old_ids)
