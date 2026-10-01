from rag.repositories.task_repository import TaskRepository
from rag.services.indexing.types.message import IndexMessage


class IndexTaskService:
    def __init__(self, tasks: TaskRepository) -> None:
        self._tasks = tasks

    async def publish(self, message: IndexMessage) -> None:
        await self._tasks.publish(message)
