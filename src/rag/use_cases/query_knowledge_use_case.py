from rag.services.retrieval.vector_query_service import VectorQueryService
from rag.services.retrieval.types.search_result import SearchResult


class QueryKnowledgeUseCase:
    def __init__(self, vectorQueryService: VectorQueryService) -> None:
        self.vectorQueryService = vectorQueryService

    async def execute(self, text: str, top_k: int = 5) -> list[SearchResult]:
        return await self.vectorQueryService.query(text, top_k)
