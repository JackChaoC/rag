from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str
    message: str


class DocumentResponse(BaseModel):
    document_id: UUID
    source_uri: str
    title: str | None
    version: int
    status: str
    metadata: dict[str, Any]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)


class SearchItem(BaseModel):
    chunk_id: UUID
    document_id: UUID
    score: float
    content: str
    source_uri: str
    title: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]


class ChunkResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    source_uri: str
    title: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]
