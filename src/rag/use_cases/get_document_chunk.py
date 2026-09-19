from uuid import UUID

from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository, HydratedChunk
from rag.use_cases.common import NotFoundError


class GetDocumentChunk:
    def __init__(self, chunks: ChunkRepository) -> None:
        self._chunks = chunks

    async def execute(self, document_id: UUID, chunk_id: UUID) -> HydratedChunk:
        chunk = await self._chunks.get_for_document(document_id, chunk_id)
        if chunk is None:
            raise NotFoundError("chunk not found")
        return chunk
