from rag.repositories.embedding_repository import EmbeddingRepository


class EmbeddingService:
    def __init__(self, embeddingRepository: EmbeddingRepository):
        self.embeddingRepository = embeddingRepository

    async def embedNodes(self, nodes):
        return await self.embeddingRepository.embedNodes(nodes)
