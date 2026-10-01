from rag.resources.rabbitmq.broker import RabbitMQResource
from rag.services.publisher.types.message import IndexMessage


class TaskRepository:
    def __init__(self, rabbitmqResource: RabbitMQResource) -> None:
        self.rabbitmqResource = rabbitmqResource

    async def publish(self, message: IndexMessage) -> None:
        await self.rabbitmqResource.publish(message)

    async def healthcheck(self) -> bool:
        return await self.rabbitmqResource.ping()
