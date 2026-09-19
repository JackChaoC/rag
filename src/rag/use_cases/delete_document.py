from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from rag.infrastructure.database.entities.document import DocumentStatus
from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.infrastructure.messaging.models import IndexMessage, IndexOperation
from rag.use_cases.common import DependencyError, DocumentSummary, NotFoundError
from rag.use_cases.ingest_document import _summary


class DeleteDocument:
    def __init__(
        self, documents: DocumentRepository, publish: Callable[[IndexMessage], Awaitable[None]],
    ) -> None:
        self._documents = documents
        self._publish = publish

    async def execute(self, document_id: UUID) -> DocumentSummary:
        document = await self._documents.get(document_id)
        if document is None:
            raise NotFoundError("document not found")
        if document.status is DocumentStatus.DELETED:
            return _summary(document)
        await self._documents.set_status(document_id, DocumentStatus.DELETING)
        document.status = DocumentStatus.DELETING
        try:
            await self._publish(IndexMessage(document.id, IndexOperation.DELETE, document.current_version))
        except Exception as exc:
            await self._documents.set_status(
                document_id, DocumentStatus.DELETING, error=str(exc),
            )
            raise DependencyError("delete task could not be confirmed by RabbitMQ") from exc
        return _summary(document)
