from rag.repositories.index_task_repository import IndexTaskRepository
from rag.services.indexing.types.message import IndexMessage


class IndexTaskService:
    def __init__(self, tasks: IndexTaskRepository) -> None:
        self._tasks = tasks

    async def publish(self, message: IndexMessage) -> None:
        await self._tasks.publish(message)
