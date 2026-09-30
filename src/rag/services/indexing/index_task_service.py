from rag.repositories.index_task_repository import IndexTaskRepository
from rag.services.indexing.types.message import IndexMessage


class IndexTaskService:
    def __init__(self, indexTaskRepository: IndexTaskRepository) -> None:
        self.indexTaskRepository = indexTaskRepository

    async def publish(self, message: IndexMessage) -> None:
        await self.indexTaskRepository.publish(message)
