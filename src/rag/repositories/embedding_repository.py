from collections.abc import Sequence

from rag.services.embedding.interfaces.embedder import Embedder


class EmbeddingRepository:
    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return await self._embedder.embed(texts)

    async def healthcheck(self) -> bool:
        return await self._embedder.healthcheck()
