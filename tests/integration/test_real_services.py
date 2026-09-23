import asyncio
import os
from uuid import uuid4

import pytest
from qdrant_client import AsyncQdrantClient

from rag.config import Settings
from rag.infrastructure.database.client import Database
from rag.infrastructure.embedding.ollama_embedder import OllamaEmbedder
from rag.infrastructure.messaging.broker import RabbitBroker
from rag.infrastructure.messaging.models import IndexMessage, IndexOperation
from rag.infrastructure.vector_store.repositories.vector_repository import VectorRepository


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_postgres_rabbit_qdrant_and_real_ollama() -> None:
    if os.getenv("RUN_RAG_INTEGRATION") != "1":
        pytest.skip("set RUN_RAG_INTEGRATION=1 after starting local services")
    settings = Settings()
    database = Database(settings.database_url)
    broker = RabbitBroker(settings.rabbitmq_url, settings.rabbitmq_retry_delays)
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)
    embedder = OllamaEmbedder(settings.ollama_url, settings.embedding_model)
    try:
        await asyncio.wait_for(database.connect(), 15)
        await asyncio.wait_for(broker.connect(), 15)
        assert await database.ping()
        assert await broker.ping()
        vector = (await asyncio.wait_for(embedder.embed(["dimension test"]), 180))[0]
        assert len(vector) > 0
        repository = VectorRepository(qdrant, settings.qdrant_collection)
        await asyncio.wait_for(repository.ensure_collection(len(vector)), 15)
        info = await asyncio.wait_for(qdrant.get_collection(settings.qdrant_collection), 15)
        assert info.config.params.vectors.size == len(vector)
    finally:
        await embedder.aclose()
        await qdrant.close()
        await asyncio.wait_for(broker.close(), 15)
        await asyncio.wait_for(database.close(), 15)


@pytest.mark.asyncio
async def test_real_rabbit_retry_returns_to_jobs_queue() -> None:
    if os.getenv("RUN_RAG_INTEGRATION") != "1":
        pytest.skip("set RUN_RAG_INTEGRATION=1 after starting local services")
    settings = Settings()
    broker = RabbitBroker(settings.rabbitmq_url, settings.rabbitmq_retry_delays)
    message = IndexMessage(uuid4(), IndexOperation.INGEST, 1)
    attempts = 0
    completed = asyncio.Event()

    async def handler(received: IndexMessage) -> None:
        nonlocal attempts
        assert received == message
        attempts += 1
        if attempts == 1:
            raise RuntimeError("retry once")
        completed.set()

    try:
        await broker.connect()
        await broker.consume(handler)
        await broker.publish(message)
        await asyncio.wait_for(completed.wait(), 10)
        assert attempts == 2
    finally:
        await broker.close()
