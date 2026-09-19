from __future__ import annotations

from rag.core.embedding.embedder import Embedder
from rag.core.retrieval.models import SearchResult
from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository
from rag.infrastructure.vector_store.repositories.vector_repository import VectorRepository


class VectorSearch:
    def __init__(
        self, embedder: Embedder, vectors: VectorRepository, chunks: ChunkRepository,
        max_candidates: int = 100,
    ) -> None:
        self._embedder = embedder
        self._vectors = vectors
        self._chunks = chunks
        self._max_candidates = max_candidates

    async def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if not query.strip():
            raise ValueError("query must not be blank")
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")
        vector = (await self._embedder.embed([query]))[0]
        page_size = min(max(top_k * 2, 10), self._max_candidates)
        offset = 0
        output: list[SearchResult] = []
        seen: set[object] = set()
        while offset < self._max_candidates and len(output) < top_k:
            hits = await self._vectors.search(vector, min(page_size, self._max_candidates - offset), offset)
            if not hits:
                break
            hydrated = await self._chunks.hydrate([hit.chunk_id for hit in hits])
            for hit in hits:
                item = hydrated.get(hit.chunk_id)
                if item is None or hit.chunk_id in seen:
                    continue
                seen.add(hit.chunk_id)
                output.append(SearchResult(
                    item.chunk_id, item.document_id, hit.score, item.content, item.source_uri,
                    item.title, item.start_line, item.end_line, item.metadata,
                ))
                if len(output) == top_k:
                    break
            offset += len(hits)
            if len(hits) < page_size:
                break
        return output
