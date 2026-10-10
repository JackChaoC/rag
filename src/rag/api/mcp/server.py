from __future__ import annotations

from rag.services.documents.types.document import DocumentStatus, Team

from uuid import UUID

from dependency_injector import providers
from mcp.server import MCPServer

from rag.api.mcp.schemas import ChunkResult, DocumentResult, SearchResult
from rag.containers.resources import resolve
from rag.services.common.errors import NotFoundError
from rag.use_cases.get_chunk_detail_use_case import GetChunkDetailUseCase
from rag.use_cases.list_documents_use_case import ListDocumentsUseCase
from rag.use_cases.query_knowledge_use_case import QueryKnowledgeUseCase


def create_mcp_server(
    *,
    search_knowledge_provider: providers.Provider[QueryKnowledgeUseCase],
    get_document_chunk_provider: providers.Provider[GetChunkDetailUseCase],
    list_documents_provider: providers.Provider[ListDocumentsUseCase],
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
        """Get one stored chunk and its source information."""
        use_case = await resolve(get_document_chunk_provider)
        result = await use_case.execute(chunk_id)
        if result.document_id != document_id:
            raise NotFoundError("chunk not found in document")
        return ChunkResult.model_validate(result, from_attributes=True)

    @server.tool(structured_output=True)
    async def list_documents(
        q: str | None = None, team: Team | None = None,
        status: DocumentStatus | None = None, project: str | None = None,
        operator: str | None = None,
    ) -> list[DocumentResult]:
        """Query document summaries by keyword and exact metadata filters; omit filters to list all."""
        filters = {name: value for name, value in dict(
            q=q, team=team, status=status, project=project, operator=operator,
        ).items() if value is not None}
        use_case = await resolve(list_documents_provider)
        return [
            DocumentResult.model_validate(item, from_attributes=True)
            for item in await use_case.execute(**filters)
        ]

    return server
