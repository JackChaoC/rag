from rag.infrastructure.database.entities.document import DocumentStatus
from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.infrastructure.messaging.models import IndexMessage, IndexOperation


class RetryHandler:
    def __init__(self, documents: DocumentRepository) -> None:
        self._documents = documents

    async def handle(self, message: IndexMessage, error: Exception) -> None:
        if message.operation is IndexOperation.DELETE:
            return
        await self._documents.set_status(
            message.document_id,
            DocumentStatus.PENDING,
            error=_error_detail(error),
            expected={DocumentStatus.INDEXING},
        )


def _error_detail(error: Exception) -> str:
    detail = str(error).strip()
    if detail:
        return f"{type(error).__name__}: {detail}"[:4000]
    return type(error).__name__
