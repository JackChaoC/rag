from collections.abc import Sequence
from uuid import UUID

from rag.repositories.chunk_repository import ChunkRepository
from rag.services.documents.types.chunk import Chunk
from rag.services.documents.types.hydrated_chunk import HydratedChunk


class ChunkService:
    def __init__(self, chunks: ChunkRepository) -> None:
        self._chunks = chunks

    async def for_version(self, document_id: UUID, version: int) -> list[Chunk]:
        return await self._chunks.for_version(document_id, version)

    async def all_ids(
        self, document_id: UUID, *, exclude_version: int | None = None
    ) -> list[UUID]:
        return await self._chunks.all_ids(
            document_id, exclude_version=exclude_version
        )

    async def get_for_document(
        self, document_id: UUID, chunk_id: UUID
    ) -> HydratedChunk | None:
        return await self._chunks.get_for_document(document_id, chunk_id)

    async def hydrate(self, ids: Sequence[UUID]) -> dict[UUID, HydratedChunk]:
        return await self._chunks.hydrate(ids)
