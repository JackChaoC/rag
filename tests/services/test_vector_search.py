from uuid import uuid4

import pytest
from llama_index.core import Document
from llama_index.core.embeddings import MockEmbedding
from qdrant_client import AsyncQdrantClient

from rag.repositories.embedding_repository import EmbeddingRepository
from rag.repositories.vector_repository import VectorRepository
from rag.services.common.errors import NotFoundError
from rag.services.retrieval.chunk_lookup_service import ChunkLookupService
from rag.services.retrieval.vector_query_service import VectorQueryService
from rag.services.splitting.markdown_node_parser import MarkdownNodeParser


async def test_official_qdrant_nodes_lookup_query_and_delete():
    client = AsyncQdrantClient(location=":memory:")
    embedding = MockEmbedding(embed_dim=8)
    repository = VectorRepository(client, embedding, "test_nodes")
    try:
        documentId = uuid4()
        nodes = MarkdownNodeParser().get_nodes_from_documents(
            [
                Document(
                    id_=str(documentId),
                    text="# Doc\nintro\n## One\nbody\n## Two\nend",
                    metadata={
                        "document_id": str(documentId),
                        "version": 1,
                        "file_url": "/v1/files/test",
                        "title": "Doc",
                    },
                )
            ]
        )
        nodes = await EmbeddingRepository(embedding).embedNodes(nodes)
        await repository.add(nodes)
        await repository.add(nodes)
        chunks = await ChunkLookupService(repository).listChunks(documentId)
        assert [c.metadata["chunk_index"] for c in chunks] == [0, 1, 2]
        assert len((await client.scroll("test_nodes", limit=100))[0]) == 3
        chunk = await ChunkLookupService(repository).getChunkDetail(chunks[1].chunk_id)
        assert chunk.content == "## One\nbody"
        assert chunk.document_id == documentId
        assert chunk.metadata["heading_h1"] == "Doc"
        results = await VectorQueryService(repository).query("body", 2)
        assert len(results) == 2
        assert all(r.content and r.file_url == "/v1/files/test" for r in results)
        await client.delete_collection("test_nodes")
        await repository.add(nodes)
        assert len(await repository.listChunks(documentId)) == 3
        await repository.deleteDocument(documentId)
        await repository.deleteDocument(documentId)
        assert await repository.listChunks(documentId) == []
        with pytest.raises(NotFoundError):
            await ChunkLookupService(repository).getChunkDetail(chunks[0].chunk_id)
    finally:
        await client.close()


@pytest.mark.parametrize("query,top_k", [("", 5), ("ok", 0), ("ok", 11)])
async def test_query_validation(query, top_k):
    with pytest.raises(ValueError):
        await VectorQueryService(None).query(query, top_k)


def test_legacy_node_keeps_file_link_without_source_uri():
    from llama_index.core.schema import TextNode
    from rag.services.retrieval.chunk_lookup_service import chunkDetail
    document_id = uuid4()
    node = TextNode(id_=str(uuid4()), text="legacy content", metadata={"document_id": str(document_id), "source_uri": "legacy.md"})
    result = chunkDetail(node)
    assert result.file_url == f"/v1/files/{document_id}"
    assert "source_uri" not in result.metadata
