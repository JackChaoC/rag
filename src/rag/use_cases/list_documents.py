from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.use_cases.common import DocumentSummary
from rag.use_cases.ingest_document import _summary


class ListDocuments:
    def __init__(self, documents: DocumentRepository) -> None:
        self._documents = documents

    async def execute(self) -> list[DocumentSummary]:
        return [_summary(document) for document in await self._documents.list()]
