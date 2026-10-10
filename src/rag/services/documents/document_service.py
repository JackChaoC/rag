from rag.repositories.document_repository import DocumentRepository
from rag.services.documents.types.document_summary import DocumentSummary


class DocumentService:
    def __init__(self, documentRepository: DocumentRepository):
        self.documentRepository = documentRepository

    def lock(self, documentId):
        return self.documentRepository.lock(documentId)

    async def get(self, documentId):
        return await self.documentRepository.get(documentId)

    async def get_by_file_id(self, file_id):
        return await self.documentRepository.get_by_file_id(file_id)

    async def list(self):
        return await self.documentRepository.list()

    async def create(self, document):
        await self.documentRepository.create(document)

    async def save(self, document):
        await self.documentRepository.save(document)

    async def set_status(self, documentId, status, **kwargs):
        return await self.documentRepository.set_status(documentId, status, **kwargs)

    @staticmethod
    def summarize(document):
        return DocumentSummary(
            document.id,
            f"/v1/files/{document.file_id}",
            document.title,
            document.current_version,
            document.status,
            document.metadata,
            document.team, document.project, document.description, document.operator,
            document.last_error,
        )
