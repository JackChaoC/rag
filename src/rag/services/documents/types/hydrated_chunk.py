from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class HydratedChunk:
    chunk_id: UUID
    document_id: UUID
    content: str
    source_uri: str
    title: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]
