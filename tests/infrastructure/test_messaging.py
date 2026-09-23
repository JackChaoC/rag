from uuid import uuid4

import pytest

from rag.infrastructure.messaging.broker import RabbitBroker
from rag.infrastructure.messaging.models import IndexMessage, IndexOperation


class Exchange:
    def __init__(self):
        self.published = []

    async def publish(self, message, routing_key, mandatory):
        self.published.append((message, routing_key, mandatory))


class Queue:
    async def consume(self, callback, no_ack):
        self.callback = callback
        self.no_ack = no_ack


class Incoming:
    def __init__(self, message, retry_count=0, routing_key=None, original_routing_key=None):
        self.body = message.encode()
        self.headers = {"x-retry-count": retry_count}
        if original_routing_key is not None:
            self.headers["x-original-routing-key"] = original_routing_key
        self.routing_key = routing_key or message.operation.routing_key
        self.acked = False

    async def ack(self):
        self.acked = True


@pytest.mark.asyncio
async def test_recoverable_failure_is_confirmed_to_retry_before_ack() -> None:
    broker = RabbitBroker("amqp://unused", (1, 5, 30))
    broker.main_queue = Queue()
    broker.retry_exchange = Exchange()
    broker.dead_exchange = Exchange()
    message = IndexMessage(uuid4(), IndexOperation.INGEST, 1)
    retries = []

    async def fail(_routing_key, _message):
        raise RuntimeError("temporary")

    async def on_retry(retried_message, error):
        retries.append((retried_message, str(error)))

    await broker.consume(fail, on_retry=on_retry)
    incoming = Incoming(message)
    await broker.main_queue.callback(incoming)

    retried, routing_key, mandatory = broker.retry_exchange.published[0]
    assert routing_key == "retry.1"
    assert retried.headers["x-retry-count"] == 1
    assert retried.headers["x-original-routing-key"] == "document.ingest"
    assert mandatory is True
    assert retries == [(message, "temporary")]
    assert incoming.acked is True


@pytest.mark.asyncio
async def test_fourth_failure_is_dead_lettered_and_marked_failed() -> None:
    broker = RabbitBroker("amqp://unused", (1, 5, 30))
    broker.main_queue = Queue()
    broker.retry_exchange = Exchange()
    broker.dead_exchange = Exchange()
    message = IndexMessage(uuid4(), IndexOperation.REINDEX, 2)
    dead = []
    retries = []

    async def fail(_routing_key, _message):
        raise RuntimeError("terminal")

    async def on_dead(failed_message, error):
        dead.append((failed_message, str(error)))

    async def on_retry(retried_message, error):
        retries.append((retried_message, str(error)))

    await broker.consume(fail, on_dead, on_retry)
    incoming = Incoming(message, retry_count=3)
    await broker.main_queue.callback(incoming)

    assert dead == [(message, "terminal")]
    assert retries == []
    assert broker.dead_exchange.published[0][1] == "document.failed"
    assert incoming.acked is True


@pytest.mark.asyncio
async def test_retry_restores_original_operation_routing_key() -> None:
    broker = RabbitBroker("amqp://unused", (1, 5, 30))
    broker.main_queue = Queue()
    message = IndexMessage(uuid4(), IndexOperation.REINDEX, 2)
    received = []

    async def handle(routing_key, received_message):
        received.append((routing_key, received_message))

    await broker.consume(handle)
    incoming = Incoming(
        message,
        retry_count=1,
        routing_key="retry.1",
        original_routing_key="document.reindex",
    )
    await broker.main_queue.callback(incoming)

    assert received == [("document.reindex", message)]
    assert incoming.acked is True
