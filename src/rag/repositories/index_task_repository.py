from rag.resources.messaging.broker import RabbitBroker
from rag.services.indexing.types.message import IndexMessage


class IndexTaskRepository:
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker

    async def publish(self, message: IndexMessage) -> None:
        await self._broker.publish(message)
