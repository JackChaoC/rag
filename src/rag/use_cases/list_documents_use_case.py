from rag.services.documents.document_service import DocumentService


class ListDocumentsUseCase:
    def __init__(self, documentService: DocumentService) -> None:
        self.documentService = documentService

    async def execute(self):
        return [
            self.documentService.summarize(document)
            for document in await self.documentService.list()
        ]
