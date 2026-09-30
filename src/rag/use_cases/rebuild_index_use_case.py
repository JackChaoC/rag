from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus
from rag.services.publisher.publish_ingestion_document_task_service import (
    PublishIngestionDocumentTaskService,
)
from rag.services.publisher.types.message import IndexMessage, IndexOperation


class RebuildIndexUseCase:
    def __init__(
        self,
        documentService: DocumentService,
        publishIngestionDocumentTaskService: PublishIngestionDocumentTaskService,
    ) -> None:
        self.documentService = documentService
        self.publishIngestionDocumentTaskService = publishIngestionDocumentTaskService

    async def execute(self) -> int:
        """Queue current versions for rebuilding from stored files; return document count."""
        count = 0
        for item in await self.documentService.list():
            async with self.documentService.lock(item.id):
                document = await self.documentService.get(item.id)
                if document.status not in {DocumentStatus.READY, DocumentStatus.FAILED}:
                    continue
                await self.publishIngestionDocumentTaskService.publish(
                    IndexMessage(
                        document.id, IndexOperation.REINDEX, document.current_version
                    )
                )
                await self.documentService.set_status(
                    document.id, DocumentStatus.PENDING
                )
                count += 1
        return count
