from rag.resources.rabbitmq.broker import RabbitBroker
from rag.services.indexing.types.message import IndexMessage


class TaskRepository:
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker

    async def publish(self, message: IndexMessage) -> None:
        await self._broker.publish(message)

    async def healthcheck(self) -> bool:
        return await self._broker.ping()
