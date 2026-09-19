from __future__ import annotations

from uuid import UUID

from mcp.server import MCPServer

from rag.container import Container
from rag.interfaces.http.schemas import ChunkResponse, DocumentResponse, SearchItem


def create_mcp_server(container: Container) -> MCPServer:
    server = MCPServer(
        "rag",
        instructions="Search the local knowledge store and preserve source information.",
    )

    @server.tool(structured_output=True)
    async def search_knowledge(query: str, top_k: int = 5) -> list[SearchItem]:
        """Search indexed document chunks without generating an answer."""
        return [SearchItem.model_validate(item, from_attributes=True) for item in await container.search.execute(query, top_k)]

    @server.tool(structured_output=True)
    async def get_document_chunk(document_id: UUID, chunk_id: UUID) -> ChunkResponse:
        """Get one active chunk and its source information."""
        return ChunkResponse.model_validate(await container.get_chunk.execute(document_id, chunk_id), from_attributes=True)

    @server.tool(structured_output=True)
    async def list_documents() -> list[DocumentResponse]:
        """List document summaries without returning full document content."""
        return [DocumentResponse(
            document_id=item.document_id, source_uri=item.source_uri, title=item.title,
            version=item.version, status=item.status.value, metadata=item.metadata,
        ) for item in await container.list_documents.execute()]

    return server
