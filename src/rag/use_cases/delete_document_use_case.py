from rag.services.common.errors import DependencyError, NotFoundError
from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus
from rag.services.publisher.publish_ingestion_document_task_service import (
    PublishIngestionDocumentTaskService,
)
from rag.services.publisher.types.message import IndexMessage, IndexOperation


class DeleteDocumentUseCase:
    def __init__(
        self,
        documentService: DocumentService,
        publishIngestionDocumentTaskService: PublishIngestionDocumentTaskService,
    ) -> None:
        self.documentService = documentService
        self.publishIngestionDocumentTaskService = publishIngestionDocumentTaskService

    async def execute(self, documentId):
        async with self.documentService.lock(documentId):
            document = await self.documentService.get(documentId)
            if document is None:
                raise NotFoundError("document not found")
            if document.status is DocumentStatus.DELETED:
                return self.documentService.summarize(document)
            document.status = DocumentStatus.DELETING
            await self.documentService.set_status(documentId, document.status)
            try:
                await self.publishIngestionDocumentTaskService.publish(
                    IndexMessage(
                        documentId, IndexOperation.DELETE, document.current_version
                    )
                )
            except Exception as exc:
                await self.documentService.set_status(
                    documentId, DocumentStatus.DELETING, error=str(exc)
                )
                raise DependencyError(
                    "delete task could not be confirmed by RabbitMQ"
                ) from exc
            return self.documentService.summarize(document)
