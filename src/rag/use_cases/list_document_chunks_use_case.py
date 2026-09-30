from rag.services.retrieval.chunk_lookup_service import ChunkLookupService


class ListDocumentChunksUseCase:
    def __init__(self, chunkLookupService: ChunkLookupService) -> None:
        self.chunkLookupService = chunkLookupService

    async def execute(self, documentId):
        return await self.chunkLookupService.listChunks(documentId)
