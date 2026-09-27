from rag.services.retrieval.types.search_result import SearchResult
from rag.services.retrieval.vector_search import VectorSearch


class SearchKnowledge:
    def __init__(self, search: VectorSearch) -> None:
        self._search = search

    async def execute(self, query: str, top_k: int = 5) -> list[SearchResult]:
        return await self._search.search(query, top_k)
