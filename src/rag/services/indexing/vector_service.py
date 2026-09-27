from collections.abc import Sequence
from uuid import UUID

from rag.repositories.vector_repository import VectorRepository
from rag.services.indexing.types.vector_record import VectorRecord
from rag.services.retrieval.types.search_hit import SearchHit


class VectorService:
    def __init__(self, vectors: VectorRepository) -> None:
        self._vectors = vectors

    async def ensure_collection(self, dimension: int) -> None:
        await self._vectors.ensure_collection(dimension)

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        await self._vectors.upsert(records)

    async def delete(self, ids: Sequence[UUID]) -> None:
        await self._vectors.delete(ids)

    async def search(
        self, vector: list[float], limit: int, offset: int = 0
    ) -> list[SearchHit]:
        return await self._vectors.search(vector, limit, offset)

    async def recreate(self, dimension: int) -> None:
        await self._vectors.recreate(dimension)
