from rag.repositories.index_task_repository import IndexTaskRepository
from rag.services.publisher.types.message import IndexMessage


class PublishIngestionDocumentTaskService:
    def __init__(self, indexTaskRepository: IndexTaskRepository) -> None:
        self.indexTaskRepository = indexTaskRepository

    async def publish(self, message: IndexMessage) -> None:
        await self.indexTaskRepository.publish(message)
