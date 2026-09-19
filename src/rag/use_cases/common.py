from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from rag.infrastructure.database.entities.document import DocumentStatus


class NotFoundError(LookupError):
    pass


class ConflictError(RuntimeError):
    pass


class DependencyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    document_id: UUID
    source_uri: str
    title: str | None
    version: int
    status: DocumentStatus
    metadata: dict[str, Any]
