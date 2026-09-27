from __future__ import annotations

from uuid import UUID

from rag.services.common.errors import DependencyError, NotFoundError
from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus
from rag.services.documents.types.document_summary import DocumentSummary
from rag.services.indexing.index_task_service import IndexTaskService
from rag.services.indexing.types.message import IndexMessage, IndexOperation


class DeleteDocument:
    def __init__(self, documents: DocumentService, tasks: IndexTaskService) -> None:
        self._documents = documents
        self._tasks = tasks

    async def execute(self, document_id: UUID) -> DocumentSummary:
        document = await self._documents.get(document_id)
        if document is None:
            raise NotFoundError("document not found")
        if document.status is DocumentStatus.DELETED:
            return self._documents.summarize(document)
        await self._documents.set_status(document_id, DocumentStatus.DELETING)
        document.status = DocumentStatus.DELETING
        try:
            await self._tasks.publish(
                IndexMessage(
                    document.id, IndexOperation.DELETE, document.current_version
                )
            )
        except Exception as exc:
            await self._documents.set_status(
                document_id,
                DocumentStatus.DELETING,
                error=str(exc),
            )
            raise DependencyError(
                "delete task could not be confirmed by RabbitMQ"
            ) from exc
        return self._documents.summarize(document)
