from uuid import UUID

from rag.services.common.errors import NotFoundError
from rag.services.documents.chunk_service import ChunkService
from rag.services.documents.types.hydrated_chunk import HydratedChunk


class GetDocumentChunk:
    def __init__(self, chunks: ChunkService) -> None:
        self._chunks = chunks

    async def execute(self, document_id: UUID, chunk_id: UUID) -> HydratedChunk:
        chunk = await self._chunks.get_for_document(document_id, chunk_id)
        if chunk is None:
            raise NotFoundError("chunk not found")
        return chunk
