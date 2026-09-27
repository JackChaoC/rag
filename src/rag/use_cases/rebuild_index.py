from rag.services.documents.chunk_service import ChunkService
from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus
from rag.services.embedding.embedding_service import EmbeddingService
from rag.services.embedding.text import document_embedding_text
from rag.services.indexing.types.vector_record import VectorRecord
from rag.services.indexing.vector_service import VectorService


class RebuildIndex:
    def __init__(
        self,
        documents: DocumentService,
        chunks: ChunkService,
        embedder: EmbeddingService,
        vectors: VectorService,
    ) -> None:
        self._documents = documents
        self._chunks = chunks
        self._embedder = embedder
        self._vectors = vectors

    async def execute(self) -> int:
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
            embeddings = await self._embedder.embed(
                [
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
                ]
            )
            await self._vectors.ensure_collection(len(embeddings[0]))
            await self._vectors.upsert(
                [
                    VectorRecord(chunk.id, vector)
                    for chunk, vector in zip(chunks, embeddings, strict=True)
                ]
            )
            count += len(chunks)
        return count
