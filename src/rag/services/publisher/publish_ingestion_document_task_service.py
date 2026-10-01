from rag.repositories.task_repository import TaskRepository
from rag.services.publisher.types.message import IndexMessage


class PublishIngestionDocumentTaskService:
    def __init__(self, taskRepository: TaskRepository) -> None:
        self.taskRepository = taskRepository

    async def publish(self, message: IndexMessage) -> None:
        await self.taskRepository.publish(message)
