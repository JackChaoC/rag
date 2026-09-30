from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus
from rag.services.publisher.types.message import IndexOperation
from rag.services.vector.vector_service import VectorService


class FinalizeIndexFailureUseCase:
    def __init__(
        self, documentService: DocumentService, vectorService: VectorService
    ) -> None:
        self.documentService = documentService
        self.vectorService = vectorService

    async def execute(self, message, error):
        async with self.documentService.lock(message.document_id):
            document = await self.documentService.get(message.document_id)
            if document is None or document.current_version != message.version:
                return
            if document.status in {DocumentStatus.READY, DocumentStatus.DELETED}:
                return
            if message.operation is not IndexOperation.DELETE:
                if document.status is DocumentStatus.DELETING:
                    return
                await self.vectorService.deleteDocument(document.id)
            status = (
                DocumentStatus.DELETING
                if message.operation is IndexOperation.DELETE
                else DocumentStatus.FAILED
            )
            await self.documentService.set_status(
                document.id, status, error=str(error)[:4000]
            )
