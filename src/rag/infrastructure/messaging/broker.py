from __future__ import annotations

from collections.abc import Awaitable, Callable

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, IncomingMessage, Message

from rag.infrastructure.messaging.models import IndexMessage

MAIN_EXCHANGE = "rag.indexing"
MAIN_QUEUE = "rag.indexing.jobs"
RETRY_EXCHANGE = "rag.indexing.retry"
DEAD_EXCHANGE = "rag.indexing.dlx"
DEAD_QUEUE = "rag.indexing.dead"


class RabbitBroker:
    def __init__(self, url: str, retry_delays: tuple[int, int, int], prefetch: int = 4) -> None:
        self._url = url
        self._retry_delays = retry_delays
        self._prefetch = prefetch
        self.connection: aio_pika.abc.AbstractRobustConnection | None = None
        self.channel: aio_pika.abc.AbstractRobustChannel | None = None
        self.main_exchange: aio_pika.abc.AbstractExchange | None = None
        self.retry_exchange: aio_pika.abc.AbstractExchange | None = None
        self.dead_exchange: aio_pika.abc.AbstractExchange | None = None
        self.main_queue: aio_pika.abc.AbstractQueue | None = None

    async def connect(self) -> None:
        self.connection = await aio_pika.connect_robust(self._url)
        self.channel = await self.connection.channel(publisher_confirms=True, on_return_raises=True)
        await self.channel.set_qos(prefetch_count=self._prefetch)
        await self._declare_topology()

    async def _declare_topology(self) -> None:
        assert self.channel is not None
        self.main_exchange = await self.channel.declare_exchange(MAIN_EXCHANGE, ExchangeType.DIRECT, durable=True)
        self.retry_exchange = await self.channel.declare_exchange(RETRY_EXCHANGE, ExchangeType.DIRECT, durable=True)
        self.dead_exchange = await self.channel.declare_exchange(DEAD_EXCHANGE, ExchangeType.DIRECT, durable=True)
        self.main_queue = await self.channel.declare_queue(
            MAIN_QUEUE, durable=True, arguments={"x-dead-letter-exchange": DEAD_EXCHANGE},
        )
        for key in ("document.ingest", "document.reindex", "document.delete"):
            await self.main_queue.bind(self.main_exchange, key)
        for index in range(1, 4):
            await self.main_queue.bind(self.main_exchange, f"retry.{index}")
        dead = await self.channel.declare_queue(DEAD_QUEUE, durable=True)
        await dead.bind(self.dead_exchange, "document.failed")
        for index, delay in enumerate(self._retry_delays, start=1):
            queue = await self.channel.declare_queue(
                f"rag.indexing.retry.{index}", durable=True,
                arguments={
                    "x-message-ttl": delay * 1000,
                    "x-dead-letter-exchange": MAIN_EXCHANGE,
                },
            )
            await queue.bind(self.retry_exchange, f"retry.{index}")

    async def publish(self, message: IndexMessage) -> None:
        if self.main_exchange is None:
            raise RuntimeError("RabbitMQ is not connected")
        await self.main_exchange.publish(
            Message(message.encode(), delivery_mode=DeliveryMode.PERSISTENT),
            routing_key=message.operation.routing_key,
            mandatory=True,
        )

    async def consume(
        self, handler: Callable[[str, IndexMessage], Awaitable[None]],
        on_dead: Callable[[IndexMessage, Exception], Awaitable[None]] | None = None,
    ) -> None:
        if self.main_queue is None:
            raise RuntimeError("RabbitMQ is not connected")

        async def callback(incoming: IncomingMessage) -> None:
            message = IndexMessage.decode(incoming.body)
            retry_count = int(incoming.headers.get("x-retry-count", 0))
            routing_key = _operation_routing_key(incoming)
            try:
                await handler(routing_key, message)
            except Exception as exc:
                if retry_count < 3:
                    assert self.retry_exchange is not None
                    await self.retry_exchange.publish(
                        Message(
                            incoming.body, delivery_mode=DeliveryMode.PERSISTENT,
                            headers={
                                "x-retry-count": retry_count + 1,
                                "x-last-error": str(exc)[:512],
                                "x-original-routing-key": routing_key,
                            },
                        ),
                        routing_key=f"retry.{retry_count + 1}", mandatory=True,
                    )
                else:
                    if on_dead is not None:
                        await on_dead(message, exc)
                    assert self.dead_exchange is not None
                    await self.dead_exchange.publish(
                        Message(
                            incoming.body, delivery_mode=DeliveryMode.PERSISTENT,
                            headers={"x-retry-count": retry_count, "x-last-error": str(exc)[:512]},
                        ),
                        routing_key="document.failed", mandatory=True,
                    )
                await incoming.ack()
            else:
                await incoming.ack()

        await self.main_queue.consume(callback, no_ack=False)

    async def ping(self) -> bool:
        return bool(self.connection and not self.connection.is_closed)

    async def close(self) -> None:
        if self.connection is not None:
            await self.connection.close()


def _operation_routing_key(incoming: IncomingMessage) -> str:
    value = incoming.headers.get("x-original-routing-key", incoming.routing_key)
    if isinstance(value, bytes):
        return value.decode()
    return str(value)
