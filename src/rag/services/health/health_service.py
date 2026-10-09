import asyncio
from collections.abc import Awaitable, Callable

from rag.repositories.document_repository import DocumentRepository
from rag.repositories.embedding_repository import EmbeddingRepository
from rag.repositories.task_repository import TaskRepository
from rag.repositories.vector_repository import VectorRepository
from rag.services.health.types.health_status import HealthStatus


class HealthService:
    def __init__(
        self,
        documentRepository: DocumentRepository,
        taskRepository: TaskRepository,
        vectorRepository: VectorRepository,
        embeddingRepository: EmbeddingRepository,
    ) -> None:
        self.documentRepository = documentRepository
        self.taskRepository = taskRepository
        self.vectorRepository = vectorRepository
        self.embeddingRepository = embeddingRepository

    async def check(self) -> HealthStatus:
        results = await asyncio.gather(
            self._check(self.documentRepository.healthcheck),
            self._check(self.taskRepository.healthcheck),
            self._check(self.vectorRepository.healthcheck),
            self._check(self.embeddingRepository.healthcheck),
            self._check(self.taskRepository.worker_healthcheck),
        )
        checks = dict(zip(("postgresql", "rabbitmq", "qdrant", "ollama", "worker"), results))
        return HealthStatus(ready=all(checks.values()), dependencies=checks)

    @staticmethod
    async def _check(checker: Callable[[], Awaitable[bool]]) -> bool:
        try:
            return await checker()
        except Exception:
            return False
