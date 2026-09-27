from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DocumentResult(BaseModel):
    document_id: UUID
    source_uri: str
    title: str | None
    version: int
    status: str
    metadata: dict[str, Any]


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    score: float
    content: str
    source_uri: str
    title: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]


class ChunkResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    source_uri: str
    title: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]
