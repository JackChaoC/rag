import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from dependency_injector import providers
from mcp import Client

from rag.api.http.app import create_app
from rag.api.mcp.server import create_mcp_server
from rag.containers import create_container
from rag.containers.resources import container_lifespan, resolve


def resource_container(events, fail=None):
    container = create_container()

    @asynccontextmanager
    async def resource(name):
        events.append("start " + name)
        try:
            if name == fail:
                raise RuntimeError("startup failed")
            yield SimpleNamespace(
                require_session_factory=lambda: object(),
                publish=AsyncMock(),
            )
        finally:
            events.append("close " + name)

    for name in ("postgresql", "qdrant", "ollama", "rabbitmq"):
        getattr(container.resources, name).override(providers.Resource(resource, name))
    return container


@pytest.mark.asyncio
async def test_singletons_are_shared_within_container_and_isolated_between_containers():
    first = resource_container([])
    second = resource_container([])
    names = (
        "repositories.documents",
        "repositories.chunks",
        "repositories.vectors",
        "services.documents",
        "services.chunks",
        "services.embeddings",
        "services.vectors",
        "services.index_tasks",
        "services.health",
        "services.vector_search",
        "use_cases.delete_document",
        "use_cases.list_documents",
        "use_cases.get_document_chunk",
        "use_cases.search_knowledge",
        "use_cases.check_health",
        "use_cases.index_document",
        "use_cases.delete_document_index",
        "use_cases.finalize_index_failure",
        "use_cases.rebuild_index",
        "worker.document_ingest_handler",
        "worker.document_reindex_handler",
        "worker.document_delete_handler",
        "worker.dispatcher",
        "worker.failure_handler",
        "worker.rebuild_handler",
    )
    async with container_lifespan(first), container_lifespan(second):
        for name in names:
            layer, provider_name = name.split(".")
            provider = getattr(getattr(first, layer), provider_name)
            a, b = await asyncio.gather(resolve(provider), resolve(provider))
            assert a is b, name
            assert a is not await resolve(
                getattr(getattr(second, layer), provider_name)
            ), name
        ingest = await resolve(first.worker.document_ingest_handler)
        reindex = await resolve(first.worker.document_reindex_handler)
        assert ingest._index_document is reindex._index_document


@pytest.mark.asyncio
async def test_parser_owners_remain_independent_but_share_repositories():
    container = resource_container([])
    container.services.parser.override(providers.Factory(object))
    async with container_lifespan(container):
        for name in ("ingest_document", "reindex_document"):
            provider = getattr(container.use_cases, name)
            a, b = await resolve(provider), await resolve(provider)
            assert a is not b
            assert a._processing is not b._processing
            assert a._processing._parser is not b._processing._parser
            assert a._documents is b._documents


@pytest.mark.asyncio
async def test_use_cases_and_worker_share_overridden_repository():
    container = resource_container([])
    fake_documents = SimpleNamespace(list=AsyncMock(return_value=[]))
    with container.repositories.documents.override(providers.Object(fake_documents)):
        async with container_lifespan(container):
            use_case = await resolve(container.use_cases.list_documents)
            indexer = await resolve(container.use_cases.index_document)
            delete_handler = await resolve(container.worker.document_delete_handler)
            document_service = await resolve(container.services.documents)
            assert document_service._documents is fake_documents
            assert use_case._documents is document_service
            assert indexer._documents is document_service
            assert delete_handler._delete_document_index._documents is document_service
            assert await use_case.execute() == []


@pytest.mark.asyncio
async def test_lifespan_restart_rebuilds_singletons_with_fresh_resources():
    container = resource_container([])
    async with container_lifespan(container):
        before = await resolve(container.repositories.vectors)
    async with container_lifespan(container):
        after = await resolve(container.repositories.vectors)
        assert after is not before
        assert after._client is not before._client
        assert after._client is await resolve(container.resources.qdrant)


@pytest.mark.asyncio
async def test_override_and_singleton_reset_rebind_consumers():
    container = resource_container([])
    async with container_lifespan(container):
        original = await resolve(container.use_cases.list_documents)
        fake = SimpleNamespace(list=AsyncMock(return_value=[]))
        with container.repositories.documents.override(providers.Object(fake)):
            with container.reset_singletons():
                service = await resolve(container.use_cases.list_documents)
                assert service is not original
                assert await service.execute() == []
                fake.list.assert_awaited_once()
        restored = await resolve(container.use_cases.list_documents)
        assert restored._documents is not fake


@pytest.mark.asyncio
async def test_health_service_uses_each_service_repository_healthcheck():
    container = resource_container([])
    repositories = {
        name: SimpleNamespace(healthcheck=AsyncMock(return_value=True))
        for name in ("documents", "tasks", "vectors", "embeddings")
    }
    with (
        container.repositories.documents.override(
            providers.Object(repositories["documents"])
        ),
        container.repositories.tasks.override(providers.Object(repositories["tasks"])),
        container.repositories.vectors.override(
            providers.Object(repositories["vectors"])
        ),
        container.repositories.embeddings.override(
            providers.Object(repositories["embeddings"])
        ),
    ):
        async with container_lifespan(container):
            status = await (await resolve(container.services.health)).check()
    assert status.ready
    assert status.dependencies == {
        "postgresql": True,
        "rabbitmq": True,
        "qdrant": True,
        "ollama": True,
    }
    for repository in repositories.values():
        repository.healthcheck.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, "ollama"])
async def test_resource_cleanup_on_success_and_partial_startup(failure):
    events = []
    container = resource_container(events, failure)
    if failure:
        with pytest.raises(RuntimeError, match="startup failed"):
            async with container_lifespan(container):
                pytest.fail("must not enter application")
        assert events == [
            "start postgresql",
            "start qdrant",
            "start ollama",
            "close ollama",
            "close qdrant",
            "close postgresql",
        ]
    else:
        async with container_lifespan(container):
            first = await resolve(container.resources.postgresql)
            assert await resolve(container.resources.postgresql) is first
            assert await resolve(container.repositories.documents) is await resolve(
                container.repositories.documents
            )
            await resolve(container.worker.dispatcher)
        assert events[-4:] == [
            "close rabbitmq",
            "close ollama",
            "close qdrant",
            "close postgresql",
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
        "close rabbitmq",
        "close ollama",
        "close qdrant",
        "close postgresql",
    ]


@pytest.mark.asyncio
async def test_http_and_mcp_share_async_provider_and_override_restores():
    events = []
    container = resource_container(events)
    original = SimpleNamespace(execute=AsyncMock(return_value=[]))
    replacement = SimpleNamespace(execute=AsyncMock(return_value=[]))

    async def make_search():
        return original

    container.use_cases.search_knowledge.override(providers.Coroutine(make_search))
    app = create_app(container)
    server = create_mcp_server(
        search_knowledge_provider=container.use_cases.search_knowledge,
        get_document_chunk_provider=container.use_cases.get_document_chunk,
        list_documents_provider=container.use_cases.list_documents,
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
        with container.use_cases.search_knowledge.override(
            providers.Object(replacement)
        ):
            assert (
                await http.post("/v1/search", json={"query": "second"})
            ).status_code == 200
            result = await mcp.call_tool("search_knowledge", {"query": "third"})
            assert not result.is_error
        assert await resolve(container.use_cases.search_knowledge) is original
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
        "close rabbitmq",
        "close ollama",
        "close qdrant",
        "close postgresql",
    ]
