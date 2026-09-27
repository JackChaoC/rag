from collections.abc import Sequence
from uuid import UUID

from rag.repositories.document_repository import DocumentRepository
from rag.services.documents.types.chunk import Chunk
from rag.services.documents.types.document import Document, DocumentStatus
from rag.services.documents.types.document_summary import DocumentSummary


class DocumentService:
    def __init__(self, documents: DocumentRepository) -> None:
        self._documents = documents

    async def get(self, document_id: UUID) -> Document | None:
        return await self._documents.get(document_id)

    async def get_by_source_uri(self, source_uri: str) -> Document | None:
        return await self._documents.get_by_source_uri(source_uri)

    async def list(self) -> list[Document]:
        return await self._documents.list()

    async def create_with_chunks(
        self, document: Document, chunks: Sequence[Chunk]
    ) -> None:
        await self._documents.create_with_chunks(document, chunks)

    async def add_version(self, document: Document, chunks: Sequence[Chunk]) -> None:
        await self._documents.add_version(document, chunks)

    async def set_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        *,
        error: str | None = None,
        expected: set[DocumentStatus] | None = None,
    ) -> bool:
        return await self._documents.set_status(
            document_id, status, error=error, expected=expected
        )

    async def activate_version(self, document_id: UUID, version: int) -> None:
        await self._documents.activate_version(document_id, version)

    async def mark_deleted(self, document_id: UUID) -> None:
        await self._documents.mark_deleted(document_id)

    @staticmethod
    def summarize(document: Document) -> DocumentSummary:
        return DocumentSummary(
            document.id,
            document.source_uri,
            document.title,
            document.current_version,
            document.status,
            document.metadata,
        )
