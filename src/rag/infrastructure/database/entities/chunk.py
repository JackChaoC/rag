from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(slots=True)
class Chunk:
    id: UUID
    document_id: UUID
    version: int
    chunk_index: int
    content: str
    start_line: int | None = None
    end_line: int | None = None
    token_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    active: bool = False
    created_at: datetime | None = None
