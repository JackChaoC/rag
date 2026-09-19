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
    def __init__(self, message, retry_count=0):
        self.body = message.encode()
        self.headers = {"x-retry-count": retry_count}
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

    async def fail(_message):
        raise RuntimeError("temporary")

    await broker.consume(fail)
    incoming = Incoming(message)
    await broker.main_queue.callback(incoming)

    retried, routing_key, mandatory = broker.retry_exchange.published[0]
    assert routing_key == "retry.1"
    assert retried.headers["x-retry-count"] == 1
    assert retried.headers["x-original-routing-key"] == "document.ingest"
    assert mandatory is True
    assert incoming.acked is True


@pytest.mark.asyncio
async def test_fourth_failure_is_dead_lettered_and_marked_failed() -> None:
    broker = RabbitBroker("amqp://unused", (1, 5, 30))
    broker.main_queue = Queue()
    broker.retry_exchange = Exchange()
    broker.dead_exchange = Exchange()
    message = IndexMessage(uuid4(), IndexOperation.REINDEX, 2)
    dead = []

    async def fail(_message):
        raise RuntimeError("terminal")

    async def on_dead(failed_message, error):
        dead.append((failed_message, str(error)))

    await broker.consume(fail, on_dead)
    incoming = Incoming(message, retry_count=3)
    await broker.main_queue.callback(incoming)

    assert dead == [(message, "terminal")]
    assert broker.dead_exchange.published[0][1] == "document.failed"
    assert incoming.acked is True
