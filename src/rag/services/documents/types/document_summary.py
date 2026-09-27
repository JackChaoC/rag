from dataclasses import dataclass
from typing import Any
from uuid import UUID

from rag.services.documents.types.document import DocumentStatus


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    document_id: UUID
    source_uri: str
    title: str | None
    version: int
    status: DocumentStatus
    metadata: dict[str, Any]
