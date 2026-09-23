from rag.infrastructure.database.entities.document import DocumentStatus
from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository
from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.infrastructure.messaging.models import IndexMessage, IndexOperation
from rag.infrastructure.vector_store.repositories.vector_repository import VectorRepository


class FailureHandler:
    def __init__(
        self,
        documents: DocumentRepository,
        chunks: ChunkRepository,
        vectors: VectorRepository,
    ) -> None:
        self._documents = documents
        self._chunks = chunks
        self._vectors = vectors

    async def handle(self, message: IndexMessage, error: Exception) -> None:
        if message.operation is not IndexOperation.DELETE:
            target = await self._chunks.for_version(
                message.document_id,
                message.version,
            )
            await self._vectors.delete([chunk.id for chunk in target])
        await self._documents.set_status(
            message.document_id,
            DocumentStatus.FAILED,
            error=str(error)[:4000],
        )
