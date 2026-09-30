from rag.resources.messaging.broker import RabbitBrokerResource
from rag.services.publisher.types.message import IndexMessage


class IndexTaskRepository:
    def __init__(self, brokerResource: RabbitBrokerResource) -> None:
        self.brokerResource = brokerResource

    async def publish(self, message: IndexMessage) -> None:
        await self.brokerResource.publish(message)
