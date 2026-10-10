from contextlib import AsyncExitStack, asynccontextmanager
from inspect import isawaitable

from dependency_injector import containers, providers

from rag.resources.ollama.client import OllamaResource
from rag.resources.postgresql.client import PostgreSQLResource
from rag.resources.qdrant.client import QdrantResource
from rag.resources.rabbitmq.broker import RabbitMQResource


async def resolve[T](provider: providers.Provider[T]) -> T:
    """Async resources propagate awaitables; object overrides may be synchronous."""
    value = provider()
    return await value if isawaitable(value) else value


@asynccontextmanager
async def postgresql_resource(url: str):
    postgresqlResource = PostgreSQLResource(url)
    try:
        await postgresqlResource.connect()
        yield postgresqlResource
    finally:
        await postgresqlResource.close()


@asynccontextmanager
async def rabbitmq_resource(
    url: str, retry_delays: tuple[int, int, int], prefetch: int, namespace: str
):
    rabbitmqResource = RabbitMQResource(url, retry_delays, prefetch, namespace)
    try:
        await rabbitmqResource.connect()
        yield rabbitmqResource
    finally:
        await rabbitmqResource.close()


@asynccontextmanager
async def qdrant_resource(url: str):
    qdrantResource = QdrantResource(url=url)
    try:
        yield qdrantResource
    finally:
        await qdrantResource.close()


@asynccontextmanager
async def ollama_resource(url: str, model: str):
    ollamaResource = OllamaResource(url, model)
    try:
        yield ollamaResource
    finally:
        await ollamaResource.close()


class Resources(containers.DeclarativeContainer):
    config = providers.Configuration()
    postgresqlResource = providers.Resource(postgresql_resource, config.database_url)
    rabbitmqResource = providers.Resource(
        rabbitmq_resource,
        config.rabbitmq_url,
        config.rabbitmq_retry_delays,
        config.rabbitmq_prefetch,
        config.rabbitmq_namespace,
    )
    qdrantResource = providers.Resource(qdrant_resource, config.qdrant_url)
    ollamaResource = providers.Resource(
        ollama_resource,
        config.ollama_url,
        config.embedding_model,
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
            container.resources.postgresqlResource,
            container.resources.qdrantResource,
            container.resources.ollamaResource,
            container.resources.rabbitmqResource,
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
