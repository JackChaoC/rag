from contextlib import AsyncExitStack, asynccontextmanager
from inspect import isawaitable

import httpx
from dependency_injector import containers, providers
from qdrant_client import AsyncQdrantClient

from rag.infrastructure.database.client import Database
from rag.infrastructure.embedding.ollama_embedder import OllamaEmbedder
from rag.infrastructure.messaging.broker import RabbitBroker


async def resolve[T](provider: providers.Provider[T]) -> T:
    """Async resources propagate awaitables; object overrides may be synchronous."""
    value = provider()
    return await value if isawaitable(value) else value


@asynccontextmanager
async def database_resource(url: str):
    database = Database(url)
    try:
        await database.connect()
        yield database
    finally:
        await database.close()


@asynccontextmanager
async def broker_resource(url: str, retry_delays: tuple[int, int, int], prefetch: int):
    broker = RabbitBroker(url, retry_delays, prefetch)
    try:
        await broker.connect()
        yield broker
    finally:
        await broker.close()


@asynccontextmanager
async def qdrant_resource(url: str):
    client = AsyncQdrantClient(url=url)
    try:
        yield client
    finally:
        await client.close()


@asynccontextmanager
async def embedder_resource(url: str, model: str, num_gpu: int):
    embedder = OllamaEmbedder(url, model, num_gpu=num_gpu)
    try:
        yield embedder
    finally:
        await embedder.aclose()


class Resources(containers.DeclarativeContainer):
    config = providers.Configuration()
    database = providers.Resource(database_resource, config.database_url)
    broker = providers.Resource(
        broker_resource,
        config.rabbitmq_url,
        config.rabbitmq_retry_delays,
        config.rabbitmq_prefetch,
    )
    qdrant = providers.Resource(qdrant_resource, config.qdrant_url)
    embedder = providers.Resource(
        embedder_resource,
        config.ollama_url,
        config.embedding_model,
        config.ollama_num_gpu,
    )
    # Each health probe closes its own client.
    health_http_client = providers.Factory(
        httpx.AsyncClient,
        base_url=config.ollama_url,
        timeout=2,
    )


@asynccontextmanager
async def container_lifespan(container):
    # Sequential startup avoids racing initializers after a partial failure.
    # Close the broker before resources used by consumers.
    async with AsyncExitStack() as stack:
        # Discard cached services after closing resources, including on failure.
        # A restarted lifespan must resolve dependencies against fresh clients.
        stack.callback(container.reset_singletons)
        for provider in (
            container.resources.database,
            container.resources.qdrant,
            container.resources.embedder,
            container.resources.broker,
        ):
            stack.push_async_callback(_shutdown, provider)
            await resolve(provider)
        yield container


async def _shutdown(provider):
    while provider.last_overriding is not None:
        provider = provider.last_overriding
    if isinstance(provider, providers.Resource):
        result = provider.shutdown()
        if isawaitable(result):
            await result
