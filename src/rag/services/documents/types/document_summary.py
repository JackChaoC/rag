from dataclasses import dataclass
from typing import Any
from uuid import UUID

from rag.services.documents.types.document import DocumentStatus


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    document_id: UUID
    file_url: str
    title: str
    version: int
    status: DocumentStatus
    metadata: dict[str, Any]
    team: str | None = None
    project: str | None = None
    description: str | None = None
    operator: str | None = None
    last_error: str | None = None
