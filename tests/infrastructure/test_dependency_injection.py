import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from dependency_injector import providers
from mcp import Client

from rag.container import create_container
from rag.interfaces.http.app import create_app
from rag.interfaces.mcp.server import create_mcp_server
from rag.resources import container_lifespan, resolve


def resource_container(events, fail=None):
    container = create_container()

    @asynccontextmanager
    async def resource(name):
        events.append("start " + name)
        try:
            if name == fail:
                raise RuntimeError("startup failed")
            yield SimpleNamespace(require_session_factory=lambda: object())
        finally:
            events.append("close " + name)

    for name in ("database", "qdrant", "embedder", "broker"):
        getattr(container, name).override(providers.Resource(resource, name))
    return container


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

    container.health_http_client.override(providers.Factory(client_factory))
    async with container_lifespan(container):
        health = await resolve(container.check_health)
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
            first = await resolve(container.database)
            assert await resolve(container.database) is first
            assert await resolve(container.documents) is not await resolve(
                container.documents
            )
            await resolve(container.dispatcher)
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

    container.search_knowledge.override(providers.Coroutine(make_search))
    app = create_app(container)
    server = create_mcp_server(
        search_knowledge_provider=container.search_knowledge,
        get_document_chunk_provider=container.get_document_chunk,
        list_documents_provider=container.list_documents,
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
        with container.search_knowledge.override(providers.Object(replacement)):
            assert (
                await http.post("/v1/search", json={"query": "second"})
            ).status_code == 200
            result = await mcp.call_tool("search_knowledge", {"query": "third"})
            assert not result.is_error
        assert await resolve(container.search_knowledge) is original
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
