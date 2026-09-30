from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus
from rag.services.indexing.index_task_service import IndexTaskService
from rag.services.indexing.types.message import IndexMessage, IndexOperation


class RebuildIndexUseCase:
    def __init__(
        self, documentService: DocumentService, indexTaskService: IndexTaskService
    ) -> None:
        self.documentService = documentService
        self.indexTaskService = indexTaskService

    async def execute(self) -> int:
        """Queue current versions for rebuilding from stored files; return document count."""
        count = 0
        for item in await self.documentService.list():
            async with self.documentService.lock(item.id):
                document = await self.documentService.get(item.id)
                if document.status not in {DocumentStatus.READY, DocumentStatus.FAILED}:
                    continue
                await self.indexTaskService.publish(
                    IndexMessage(
                        document.id, IndexOperation.REINDEX, document.current_version
                    )
                )
                await self.documentService.set_status(
                    document.id, DocumentStatus.PENDING
                )
                count += 1
        return count
