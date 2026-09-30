from rag.services.retrieval.chunk_lookup_service import ChunkLookupService


class GetChunkDetailUseCase:
    def __init__(self, chunkLookupService: ChunkLookupService) -> None:
        self.chunkLookupService = chunkLookupService

    async def execute(self, chunkId):
        return await self.chunkLookupService.getChunkDetail(chunkId)
