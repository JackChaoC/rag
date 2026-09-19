from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from rag.core.retrieval.vector_search import VectorSearch
from rag.infrastructure.database.repositories.chunk_repository import HydratedChunk
from rag.infrastructure.vector_store.entities.search_hit import SearchHit


class FakeEmbedder:
    async def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


class FakeVectors:
    def __init__(self, pages):
        self.pages = pages

    async def search(self, vector, limit, offset=0):
        return self.pages.get(offset, [])


class FakeChunks:
    def __init__(self, values):
        self.values = values

    async def hydrate(self, ids):
        return {item: self.values[item] for item in ids if item in self.values}


@pytest.mark.asyncio
async def test_search_filters_stale_points_and_preserves_qdrant_order() -> None:
    stale, first, second = uuid4(), uuid4(), uuid4()
    document = uuid4()
    def item(chunk_id):
        return HydratedChunk(chunk_id, document, str(chunk_id), "doc.md", None, 1, 1, {})
    vectors = FakeVectors({0: [SearchHit(stale, .99), SearchHit(first, .8), SearchHit(second, .7)]})
    search = VectorSearch(FakeEmbedder(), vectors, FakeChunks({first: item(first), second: item(second)}), 10)
    result = await search.search("query", 2)
    assert [entry.chunk_id for entry in result] == [first, second]
    assert [entry.score for entry in result] == [.8, .7]
