import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from dependency_injector import providers
from llama_index.core.embeddings import MockEmbedding
from mcp import Client
from qdrant_client import AsyncQdrantClient

from rag.api.http.app import create_app
from rag.api.mcp.server import create_mcp_server
from rag.containers import create_container
from rag.containers.resources import container_lifespan, resolve


def resource_container(events, fail=None):
    container = create_container()

    @asynccontextmanager
    async def resource(name):
        events.append("start " + name)
        value = None
        try:
            if name == fail:
                raise RuntimeError("startup failed")
            if name == "qdrant":
                value = AsyncQdrantClient(location=":memory:")
            elif name == "embedder":
                value = MockEmbedding(embed_dim=8)
            else:
                value = SimpleNamespace(
                    require_session_factory=lambda: object(),
                    lockEngine=object(),
                    publish=AsyncMock(),
                )
            yield value
        finally:
            if name == "qdrant" and value:
                await value.close()
            events.append("close " + name)

    for attr, name in {
        "databaseResource": "database",
        "qdrantResource": "qdrant",
        "ollamaResource": "embedder",
        "brokerResource": "broker",
    }.items():
        getattr(container.resources, attr).override(providers.Resource(resource, name))
    return container


async def test_providers_share_services_and_keep_containers_isolated():
    first, second = resource_container([]), resource_container([])
    async with container_lifespan(first), container_lifespan(second):
        documentService = await resolve(first.services.documentService)
        assert documentService is await resolve(first.services.documentService)
        assert documentService is not await resolve(second.services.documentService)
        for name in (
            "uploadFileUseCase",
            "indexDocumentUseCase",
            "deleteDocumentIndexUseCase",
        ):
            useCase = await resolve(getattr(first.use_cases, name))
            assert useCase.documentService is documentService
        ingest = await resolve(first.worker.documentIngestHandler)
        reindex = await resolve(first.worker.documentReindexHandler)
        assert (
            ingest.indexDocumentUseCase.documentService
            is reindex.indexDocumentUseCase.documentService
        )


async def test_repository_override_reaches_worker_and_use_cases():
    container = resource_container([])
    fake = SimpleNamespace(list=AsyncMock(return_value=[]))
    with container.repositories.documentRepository.override(providers.Object(fake)):
        async with container_lifespan(container):
            useCase = await resolve(container.use_cases.listDocumentsUseCase)
            handler = await resolve(container.worker.documentDeleteHandler)
            assert useCase.documentService.documentRepository is fake
            assert (
                handler.deleteDocumentIndexUseCase.documentService
                is useCase.documentService
            )
            assert await useCase.execute() == []


async def test_lifespan_reset_discards_closed_resources():
    container = resource_container([])
    async with container_lifespan(container):
        before = await resolve(container.repositories.vectorRepository)
    async with container_lifespan(container):
        after = await resolve(container.repositories.vectorRepository)
        assert before is not after
        assert before.qdrantResource is not after.qdrantResource


@pytest.mark.asyncio
async def test_health_http_client_factory_is_injected_and_closed():
    container = resource_container([])
    clients = []

    def client_factory():
        client = httpx.AsyncClient(
            base_url="http://ollama.test",
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
        )
        clients.append(client)
        return client

    container.resources.healthHttpClientResource.override(
        providers.Factory(client_factory)
    )
    async with container_lifespan(container):
        health = await resolve(container.repositories.healthRepository)
        assert await health._check_ollama()
        assert await health._check_ollama()
    assert len(clients) == 2
    assert all(client.is_closed for client in clients)


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, "embedder"])
async def test_resource_cleanup_on_success_and_partial_startup(failure):
    events = []
    container = resource_container(events, failure)
    if failure:
        with pytest.raises(RuntimeError, match="startup failed"):
            async with container_lifespan(container):
                pytest.fail("must not enter application")
        assert events == [
            "start database",
            "start qdrant",
            "start embedder",
            "close embedder",
            "close qdrant",
            "close database",
        ]
    else:
        async with container_lifespan(container):
            first = await resolve(container.resources.databaseResource)
            assert await resolve(container.resources.databaseResource) is first
            assert await resolve(
                container.repositories.documentRepository
            ) is await resolve(container.repositories.documentRepository)
            await resolve(container.worker.dispatcher)
        assert events[-4:] == [
            "close broker",
            "close embedder",
            "close qdrant",
            "close database",
        ]


@pytest.mark.asyncio
async def test_cancellation_releases_resources():
    events = []
    container = resource_container(events)
    ready = asyncio.Event()

    async def run():
        async with container_lifespan(container):
            ready.set()
            await asyncio.Future()

    task = asyncio.create_task(run())
    await ready.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert events[-4:] == [
        "close broker",
        "close embedder",
        "close qdrant",
        "close database",
    ]


@pytest.mark.asyncio
async def test_http_and_mcp_share_async_provider_and_override_restores():
    events = []
    container = resource_container(events)
    original = SimpleNamespace(execute=AsyncMock(return_value=[]))
    replacement = SimpleNamespace(execute=AsyncMock(return_value=[]))

    async def make_search():
        return original

    container.use_cases.queryKnowledgeUseCase.override(providers.Coroutine(make_search))
    app = create_app(container)
    server = create_mcp_server(
        search_knowledge_provider=container.use_cases.queryKnowledgeUseCase,
        get_document_chunk_provider=container.use_cases.getChunkDetailUseCase,
        list_documents_provider=container.use_cases.listDocumentsUseCase,
    )
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as http,
        Client(server) as mcp,
    ):
        assert (
            await http.post("/v1/search", json={"query": "first"})
        ).status_code == 200
        with container.use_cases.queryKnowledgeUseCase.override(
            providers.Object(replacement)
        ):
            assert (
                await http.post("/v1/search", json={"query": "second"})
            ).status_code == 200
            result = await mcp.call_tool("search_knowledge", {"query": "third"})
            assert not result.is_error
        assert await resolve(container.use_cases.queryKnowledgeUseCase) is original
        assert original.execute.await_count == 1
        assert replacement.execute.await_count == 2
        tools = (await mcp.list_tools()).tools
        expected = {
            "search_knowledge": {"query", "top_k"},
            "get_document_chunk": {"document_id", "chunk_id"},
            "list_documents": set(),
        }
        for tool in tools:
            assert set(tool.input_schema.get("properties", {})) == expected[tool.name]
    assert events[-4:] == [
        "close broker",
        "close embedder",
        "close qdrant",
        "close database",
    ]
