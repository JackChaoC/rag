from collections.abc import Sequence

from rag.repositories.embedding_repository import EmbeddingRepository


class EmbeddingService:
    def __init__(self, embeddings: EmbeddingRepository) -> None:
        self._embeddings = embeddings

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return await self._embeddings.embed(texts)
