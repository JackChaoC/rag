from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SearchResult:
    chunk_id: UUID
    document_id: UUID
    score: float
    content: str
    file_url: str
    title: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]
