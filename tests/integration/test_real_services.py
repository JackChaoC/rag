import asyncio
import os
from uuid import uuid4

import pytest

from rag.config import Settings
from rag.resources.rabbitmq.broker import RabbitMQResource
from rag.services.publisher.types.message import IndexMessage, IndexOperation

pytestmark = pytest.mark.integration


async def test_real_rabbit_retry_returns_to_jobs_queue():
    if os.getenv("RUN_RAG_INTEGRATION") != "1":
        pytest.skip("set RUN_RAG_INTEGRATION=1 after starting local services")
    settings = Settings()
    namespace = f"rag.llama-index.test.{uuid4().hex}"
    broker = RabbitMQResource(settings.rabbitmq_url, (1, 1, 1), namespace=namespace)
    message = IndexMessage(uuid4(), IndexOperation.INGEST, 1)
    attempts = 0
    completed = asyncio.Event()

    async def handler(routing_key, received):
        nonlocal attempts
        assert received == message
        assert routing_key == "document.ingest"
        attempts += 1
        if attempts == 1:
            raise RuntimeError("retry once")
        completed.set()

    try:
        await broker.connect()
        await broker.consume(handler)
        await broker.publish(message)
        await asyncio.wait_for(completed.wait(), 15)
        assert attempts == 2
    finally:
        if broker.channel:
            for suffix in ("jobs", "dead", "retry.1", "retry.2", "retry.3"):
                await broker.channel.queue_delete(f"{namespace}.{suffix}")
            for suffix in ("", ".retry", ".dlx"):
                await broker.channel.exchange_delete(namespace + suffix)
        await broker.close()
