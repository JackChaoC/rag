from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document_summary import DocumentSummary


class ListDocuments:
    def __init__(self, documents: DocumentService) -> None:
        self._documents = documents

    async def execute(self) -> list[DocumentSummary]:
        return [
            self._documents.summarize(document)
            for document in await self._documents.list()
        ]
