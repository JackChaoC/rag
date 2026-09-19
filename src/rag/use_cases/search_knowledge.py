from rag.core.retrieval.models import SearchResult
from rag.core.retrieval.vector_search import VectorSearch


class SearchKnowledge:
    def __init__(self, search: VectorSearch) -> None:
        self._search = search

    async def execute(self, query: str, top_k: int = 5) -> list[SearchResult]:
        return await self._search.search(query, top_k)
