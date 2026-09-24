from contextlib import AsyncExitStack, asynccontextmanager
from inspect import isawaitable

from dependency_injector import providers
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


@asynccontextmanager
async def container_lifespan(container):
    # Sequential startup avoids racing initializers after a partial failure.
    # Close the broker before resources used by consumers.
    async with AsyncExitStack() as stack:
        for provider in (
            container.database,
            container.qdrant,
            container.embedder,
            container.broker,
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
