from contextlib import AsyncExitStack, asynccontextmanager
from inspect import isawaitable

import httpx
from dependency_injector import containers, providers
from llama_index.embeddings.ollama import OllamaEmbedding
from qdrant_client import AsyncQdrantClient

from rag.resources.database.client import DatabaseResource
from rag.resources.messaging.broker import RabbitBrokerResource


async def resolve[T](provider: providers.Provider[T]) -> T:
    """Async resources propagate awaitables; object overrides may be synchronous."""
    value = provider()
    return await value if isawaitable(value) else value


@asynccontextmanager
async def database_resource(url: str):
    databaseResource = DatabaseResource(url)
    try:
        await databaseResource.connect()
        yield databaseResource
    finally:
        await databaseResource.close()


@asynccontextmanager
async def broker_resource(
    url: str, retry_delays: tuple[int, int, int], prefetch: int, namespace: str
):
    brokerResource = RabbitBrokerResource(url, retry_delays, prefetch, namespace)
    try:
        await brokerResource.connect()
        yield brokerResource
    finally:
        await brokerResource.close()


@asynccontextmanager
async def qdrant_resource(url: str):
    qdrantResource = AsyncQdrantClient(url=url)
    try:
        yield qdrantResource
    finally:
        await qdrantResource.close()


@asynccontextmanager
async def embedder_resource(url: str, model: str, num_gpu: int):
    ollamaResource = OllamaEmbedding(
        model_name=model,
        base_url=url,
        ollama_additional_kwargs={"num_gpu": num_gpu},
        client_kwargs={"timeout": 120},
    )
    try:
        yield ollamaResource
    finally:
        # OllamaEmbedding exposes no public close; pinned adapter owns these SDK clients.
        ollamaResource._client._client.close()
        await ollamaResource._async_client._client.aclose()


class Resources(containers.DeclarativeContainer):
    config = providers.Configuration()
    databaseResource = providers.Resource(database_resource, config.database_url)
    brokerResource = providers.Resource(
        broker_resource,
        config.rabbitmq_url,
        config.rabbitmq_retry_delays,
        config.rabbitmq_prefetch,
        config.rabbitmq_namespace,
    )
    qdrantResource = providers.Resource(qdrant_resource, config.qdrant_url)
    ollamaResource = providers.Resource(
        embedder_resource,
        config.ollama_url,
        config.embedding_model,
        config.ollama_num_gpu,
    )
    # Each health probe closes its own client.
    healthHttpClientResource = providers.Factory(
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
            container.resources.databaseResource,
            container.resources.qdrantResource,
            container.resources.ollamaResource,
            container.resources.brokerResource,
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
