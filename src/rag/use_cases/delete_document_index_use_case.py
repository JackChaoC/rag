from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus
from rag.services.files.file_service import FileService
from rag.services.vector.vector_service import VectorService


class DeleteDocumentIndexUseCase:
    def __init__(
        self,
        documentService: DocumentService,
        fileService: FileService,
        vectorService: VectorService,
    ) -> None:
        self.documentService = documentService
        self.fileService = fileService
        self.vectorService = vectorService

    async def execute(self, message):
        async with self.documentService.lock(message.document_id):
            document = await self.documentService.get(message.document_id)
            if document is None:
                raise LookupError("document not found")
            if message.version < document.current_version:
                return
            if message.version > document.current_version:
                raise RuntimeError("message version is newer than document")
            await self.vectorService.deleteDocument(document.id)
            await self.fileService.delete(document.file_path)
            await self.documentService.set_status(document.id, DocumentStatus.DELETED)
