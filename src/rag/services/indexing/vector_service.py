from rag.repositories.vector_repository import VectorRepository


class VectorService:
    def __init__(self, vectorRepository: VectorRepository):
        self.vectorRepository = vectorRepository

    async def add(self, nodes):
        await self.vectorRepository.add(nodes)

    async def deleteDocument(self, documentId):
        await self.vectorRepository.deleteDocument(documentId)
