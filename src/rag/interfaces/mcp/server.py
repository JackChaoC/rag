from __future__ import annotations

from uuid import UUID

from dependency_injector import providers
from mcp.server import MCPServer

from rag.interfaces.mcp.schemas import ChunkResult, DocumentResult, SearchResult
from rag.resources import resolve
from rag.use_cases.get_document_chunk import GetDocumentChunk
from rag.use_cases.list_documents import ListDocuments
from rag.use_cases.search_knowledge import SearchKnowledge


def create_mcp_server(
    *,
    search_knowledge_provider: providers.Provider[SearchKnowledge],
    get_document_chunk_provider: providers.Provider[GetDocumentChunk],
    list_documents_provider: providers.Provider[ListDocuments],
) -> MCPServer:
    server = MCPServer(
        "rag",
        instructions="Search the local knowledge store and preserve source information.",
    )

    @server.tool(structured_output=True)
    async def search_knowledge(query: str, top_k: int = 5) -> list[SearchResult]:
        """Search indexed document chunks without generating an answer."""
        use_case = await resolve(search_knowledge_provider)
        results = await use_case.execute(query, top_k)
        return [
            SearchResult.model_validate(item, from_attributes=True) for item in results
        ]

    @server.tool(structured_output=True)
    async def get_document_chunk(document_id: UUID, chunk_id: UUID) -> ChunkResult:
        """Get one active chunk and its source information."""
        use_case = await resolve(get_document_chunk_provider)
        result = await use_case.execute(document_id, chunk_id)
        return ChunkResult.model_validate(result, from_attributes=True)

    @server.tool(structured_output=True)
    async def list_documents() -> list[DocumentResult]:
        """List document summaries without returning full document content."""
        use_case = await resolve(list_documents_provider)
        return [
            DocumentResult(
                document_id=item.document_id,
                source_uri=item.source_uri,
                title=item.title,
                version=item.version,
                status=item.status.value,
                metadata=item.metadata,
            )
            for item in await use_case.execute()
        ]

    return server
