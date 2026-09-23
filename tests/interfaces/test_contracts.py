from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from mcp import Client

from rag.infrastructure.database.entities.document import DocumentStatus
from rag.interfaces.http.app import create_app
from rag.interfaces.http.dependencies import get_check_health, get_ingest_document
from rag.interfaces.mcp.dependencies import McpDependencies
from rag.interfaces.mcp.server import create_mcp_server
from rag.use_cases.check_health import HealthStatus
from rag.use_cases.common import DependencyError, DocumentSummary


class UseCase:
    def __init__(self, value):
        self.value = value

    async def execute(self, *args, **kwargs):
        return self.value


class FailingUseCase:
    async def execute(self, *args, **kwargs):
        raise DependencyError("broker unavailable")


class FakeContainer:
    def __init__(self):
        document_id, chunk_id = uuid4(), uuid4()
        self.document_id = document_id
        self.chunk_id = chunk_id
        self.ingest = UseCase(DocumentSummary(
            document_id, "doc.md", "Doc", 1, DocumentStatus.PENDING, {},
        ))
        self.search = UseCase([])
        self.list_documents = UseCase([
            DocumentSummary(document_id, "doc.md", "Doc", 1, DocumentStatus.READY, {})
        ])
        self.get_chunk = UseCase(SimpleNamespace(
            chunk_id=chunk_id, document_id=document_id, content="text", source_uri="doc.md",
            title="Doc", start_line=1, end_line=1, metadata={},
        ))


def test_openapi_contains_public_http_contract() -> None:
    container = FakeContainer()
    app = create_app(container)  # lifespan is not entered for schema generation
    paths = app.openapi()["paths"]
    assert {
        "/v1/documents",
        "/v1/documents/{document_id}/reindex",
        "/v1/documents/{document_id}",
        "/v1/documents/{document_id}/chunks/{chunk_id}",
        "/v1/search",
        "/health",
    } <= paths.keys()


@pytest.mark.asyncio
async def test_http_validation_errors_use_stable_shape() -> None:
    app = create_app(FakeContainer())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        invalid_metadata = await client.post(
            "/v1/documents", data={"source_uri": "doc.md", "metadata": "[]"},
            files={"file": ("doc.md", b"# Doc", "text/markdown")},
        )
        unsupported = await client.post(
            "/v1/documents", data={"source_uri": "doc.docx"},
            files={"file": ("doc.docx", b"not a word file")},
        )

    assert invalid_metadata.status_code == 422
    assert invalid_metadata.json()["code"] == "invalid_input"
    assert unsupported.status_code == 422
    assert unsupported.json()["code"] == "invalid_input"


@pytest.mark.asyncio
async def test_http_rejects_top_k_above_ten() -> None:
    app = create_app(FakeContainer())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        response = await client.post("/v1/search", json={"query": "test", "top_k": 11})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_http_dependency_failure_is_503() -> None:
    container = FakeContainer()
    app = create_app(container)
    app.dependency_overrides[get_ingest_document] = lambda: FailingUseCase()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        response = await client.post(
            "/v1/documents", data={"source_uri": "doc.md"},
            files={"file": ("doc.md", b"# Doc", "text/markdown")},
        )

    assert response.status_code == 503
    assert response.json() == {
        "code": "dependency_unavailable", "message": "broker unavailable",
    }


@pytest.mark.asyncio
async def test_http_health_uses_overridable_use_case() -> None:
    app = create_app(FakeContainer())
    app.dependency_overrides[get_check_health] = lambda: UseCase(
        HealthStatus(
            ready=False,
            dependencies={
                "postgresql": True,
                "rabbitmq": True,
                "qdrant": False,
                "ollama": True,
            },
        )
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "ready": False,
        "dependencies": {
            "postgresql": True,
            "rabbitmq": True,
            "qdrant": False,
            "ollama": True,
        },
    }


@pytest.mark.asyncio
async def test_frontend_is_served_from_same_origin() -> None:
    app = create_app(FakeContainer())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test",
        follow_redirects=True,
    ) as client:
        response = await client.get("/ui/")

    assert response.status_code == 200
    assert "RAG Console" in response.text
    assert 'max="10"' in response.text


@pytest.mark.asyncio
async def test_mcp_discovers_and_calls_three_tools() -> None:
    container = FakeContainer()
    server = create_mcp_server(
        McpDependencies(
            provide_search_knowledge=lambda: container.search,
            provide_get_document_chunk=lambda: container.get_chunk,
            provide_list_documents=lambda: container.list_documents,
        )
    )
    async with Client(server) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools.tools} == {
            "search_knowledge", "get_document_chunk", "list_documents"
        }
        result = await client.call_tool("list_documents", {})
        assert result.structured_content is not None
        search = await client.call_tool("search_knowledge", {"query": "anything", "top_k": 2})
        chunk = await client.call_tool("get_document_chunk", {
            "document_id": str(container.document_id),
            "chunk_id": str(container.chunk_id),
        })
        assert search.structured_content is not None
        assert chunk.structured_content is not None
