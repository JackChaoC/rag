from rag.core.embedding.embedder import Embedder
from rag.core.embedding.text import document_embedding_text
from rag.infrastructure.database.entities.document import DocumentStatus
from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository
from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.infrastructure.vector_store.entities.vector_record import VectorRecord
from rag.infrastructure.vector_store.repositories.vector_repository import VectorRepository


class RebuildHandler:
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

    async def handle(self) -> int:
        count = 0
        for document in await self._documents.list():
            if document.status is not DocumentStatus.READY:
                continue
            chunks = await self._chunks.for_version(
                document.id,
                document.current_version,
            )
            if not chunks:
                continue
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
                for chunk in chunks
            ])
            await self._vectors.ensure_collection(len(embeddings[0]))
            await self._vectors.upsert([
                VectorRecord(chunk.id, vector)
                for chunk, vector in zip(chunks, embeddings, strict=True)
            ])
            count += len(chunks)
        return count
