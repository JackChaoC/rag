from dataclasses import dataclass

from rag.services.documents.types.document_summary import DocumentSummary


@dataclass(frozen=True, slots=True)
class DocumentPage:
    items: list[DocumentSummary]
    total: int
    page: int
    page_size: int = 20
