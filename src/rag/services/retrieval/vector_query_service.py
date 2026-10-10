from rag.repositories.vector_repository import VectorRepository
from rag.services.retrieval.chunk_lookup_service import chunkDetail
from rag.services.retrieval.types.search_result import SearchResult


class VectorQueryService:
    def __init__(self, vectorRepository: VectorRepository):
        self.vectorRepository = vectorRepository

    async def query(self, text: str, top_k: int = 5) -> list[SearchResult]:
        if not text.strip():
            raise ValueError("query must not be blank")
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        results = []
        for hit in await self.vectorRepository.query(text, top_k):
            chunk = chunkDetail(hit.node)
            results.append(
                SearchResult(
                    chunk.chunk_id,
                    chunk.document_id,
                    float(hit.score or 0),
                    chunk.content,
                    chunk.file_url,
                    chunk.title,
                    chunk.start_line,
                    chunk.end_line,
                    chunk.metadata,
                )
            )
        return results
