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
        documents: DocumentRepository,
        tasks: TaskRepository,
        vectors: VectorRepository,
        embeddings: EmbeddingRepository,
    ) -> None:
        self._documents = documents
        self._tasks = tasks
        self._vectors = vectors
        self._embeddings = embeddings

    async def check(self) -> HealthStatus:
        results = await asyncio.gather(
            self._check(self._documents.healthcheck),
            self._check(self._tasks.healthcheck),
            self._check(self._vectors.healthcheck),
            self._check(self._embeddings.healthcheck),
        )
        checks = dict(zip(("postgresql", "rabbitmq", "qdrant", "ollama"), results))
        return HealthStatus(ready=all(checks.values()), dependencies=checks)

    @staticmethod
    async def _check(checker: Callable[[], Awaitable[bool]]) -> bool:
        try:
            return await checker()
        except Exception:
            return False
