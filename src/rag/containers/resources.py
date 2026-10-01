from contextlib import AsyncExitStack, asynccontextmanager
from inspect import isawaitable

from dependency_injector import containers, providers

from rag.resources.ollama.ollama_embedder import OllamaEmbedder
from rag.resources.postgresql.client import Database
from rag.resources.qdrant.client import QdrantClient
from rag.resources.rabbitmq.broker import RabbitBroker


async def resolve[T](provider: providers.Provider[T]) -> T:
    """Async resources propagate awaitables; object overrides may be synchronous."""
    value = provider()
    return await value if isawaitable(value) else value


@asynccontextmanager
async def postgresql_resource(url: str):
    postgresql = Database(url)
    try:
        await postgresql.connect()
        yield postgresql
    finally:
        await postgresql.close()


@asynccontextmanager
async def rabbitmq_resource(url: str, retry_delays: tuple[int, int, int], prefetch: int):
    rabbitmq = RabbitBroker(url, retry_delays, prefetch)
    try:
        await rabbitmq.connect()
        yield rabbitmq
    finally:
        await rabbitmq.close()


@asynccontextmanager
async def qdrant_resource(url: str):
    client = QdrantClient(url=url)
    try:
        yield client
    finally:
        await client.close()


@asynccontextmanager
async def ollama_resource(url: str, model: str, num_gpu: int):
    ollama = OllamaEmbedder(url, model, num_gpu=num_gpu)
    try:
        yield ollama
    finally:
        await ollama.aclose()


class Resources(containers.DeclarativeContainer):
    config = providers.Configuration()
    postgresql = providers.Resource(postgresql_resource, config.database_url)
    rabbitmq = providers.Resource(
        rabbitmq_resource,
        config.rabbitmq_url,
        config.rabbitmq_retry_delays,
        config.rabbitmq_prefetch,
    )
    qdrant = providers.Resource(qdrant_resource, config.qdrant_url)
    ollama = providers.Resource(
        ollama_resource,
        config.ollama_url,
        config.embedding_model,
        config.ollama_num_gpu,
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
            container.resources.postgresql,
            container.resources.qdrant,
            container.resources.ollama,
            container.resources.rabbitmq,
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
