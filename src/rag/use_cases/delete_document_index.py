from rag.services.documents.chunk_service import ChunkService
from rag.services.documents.document_service import DocumentService
from rag.services.indexing.types.message import IndexMessage
from rag.services.indexing.vector_service import VectorService


class DeleteDocumentIndex:
    def __init__(
        self,
        documents: DocumentService,
        chunks: ChunkService,
        vectors: VectorService,
    ) -> None:
        self._documents = documents
        self._chunks = chunks
        self._vectors = vectors

    async def execute(self, message: IndexMessage) -> None:
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
