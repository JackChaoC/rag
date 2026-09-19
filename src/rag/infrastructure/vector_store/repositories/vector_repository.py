from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from qdrant_client import AsyncQdrantClient, models

from rag.infrastructure.vector_store.entities.search_hit import SearchHit
from rag.infrastructure.vector_store.entities.vector_record import VectorRecord


class VectorRepository:
    def __init__(self, client: AsyncQdrantClient, collection: str) -> None:
        self._client = client
        self._collection = collection

    async def ensure_collection(self, dimension: int) -> None:
        if not await self._client.collection_exists(self._collection):
            await self._client.create_collection(
                self._collection,
                vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
            )
            return
        info = await self._client.get_collection(self._collection)
        config = info.config.params.vectors
        if not isinstance(config, models.VectorParams) or config.size != dimension or config.distance != models.Distance.COSINE:
            raise RuntimeError("Qdrant collection vector configuration is incompatible")

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        if records:
            await self._client.upsert(
                self._collection,
                points=[models.PointStruct(id=str(record.id), vector=record.vector) for record in records],
                wait=True,
            )

    async def delete(self, ids: Sequence[UUID]) -> None:
        if ids:
            await self._client.delete(
                self._collection,
                points_selector=models.PointIdsList(points=[str(item) for item in ids]),
                wait=True,
            )

    async def search(self, vector: list[float], limit: int, offset: int = 0) -> list[SearchHit]:
        result = await self._client.query_points(
            collection_name=self._collection, query=vector, limit=limit, offset=offset,
            with_payload=False, with_vectors=False,
        )
        return [SearchHit(UUID(str(point.id)), float(point.score)) for point in result.points]

    async def recreate(self, dimension: int) -> None:
        if await self._client.collection_exists(self._collection):
            await self._client.delete_collection(self._collection)
        await self.ensure_collection(dimension)
