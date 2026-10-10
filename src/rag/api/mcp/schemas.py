from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DocumentResult(BaseModel):
    document_id: UUID
    file_url: str
    title: str
    version: int
    status: str
    metadata: dict[str, Any]


    team: str | None = None
    project: str | None = None
    description: str | None = None
    operator: str | None = None
    last_error: str | None = None


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    score: float
    content: str
    file_url: str
    title: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]


class ChunkResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    file_url: str
    title: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]
