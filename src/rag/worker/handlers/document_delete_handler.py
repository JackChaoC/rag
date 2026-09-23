from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository
from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.infrastructure.messaging.models import IndexMessage, IndexOperation
from rag.infrastructure.vector_store.repositories.vector_repository import VectorRepository


class DocumentDeleteHandler:
    def __init__(
        self,
        documents: DocumentRepository,
        chunks: ChunkRepository,
        vectors: VectorRepository,
    ) -> None:
        self._documents = documents
        self._chunks = chunks
        self._vectors = vectors

    async def handle(self, message: IndexMessage) -> None:
        if message.operation is not IndexOperation.DELETE:
            raise ValueError(
                f"DocumentDeleteHandler cannot handle {message.operation.value!r}"
            )

        document = await self._documents.get(message.document_id)
        if document is None:
            raise LookupError("document not found")
        if message.version < document.current_version:
            stale = await self._chunks.for_version(document.id, message.version)
            await self._vectors.delete([chunk.id for chunk in stale])
            return
        if message.version > document.current_version:
            raise RuntimeError("message version is newer than the document")

        point_ids = await self._chunks.all_ids(document.id)
        await self._vectors.delete(point_ids)
        await self._documents.mark_deleted(document.id)
