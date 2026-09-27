from rag.services.documents.chunk_service import ChunkService
from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus
from rag.services.indexing.types.message import IndexMessage, IndexOperation
from rag.services.indexing.vector_service import VectorService


class FinalizeIndexFailure:
    def __init__(
        self,
        documents: DocumentService,
        chunks: ChunkService,
        vectors: VectorService,
    ) -> None:
        self._documents = documents
        self._chunks = chunks
        self._vectors = vectors

    async def execute(self, message: IndexMessage, error: Exception) -> None:
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
