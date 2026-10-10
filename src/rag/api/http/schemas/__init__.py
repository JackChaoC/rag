from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rag.services.documents.types.document import Team


class ErrorResponse(BaseModel):
    code: str
    message: str


class HealthResponse(BaseModel):
    ready: bool
    dependencies: dict[str, bool]


class DocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_url: str
    title: str = Field(min_length=1)
    team: Team | None = None
    project: str | None = None
    description: str | None = None
    operator: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value):
        if not value.strip():
            raise ValueError("title is required")
        return value.strip()


class ReindexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_url: str | None = None


class FileResponse(BaseModel):
    file_id: UUID
    url: str
    filename: str
    size_bytes: int


class DocumentResponse(BaseModel):
    document_id: UUID
    file_url: str
    title: str
    version: int
    status: str
    metadata: dict[str, Any]
    team: Team | None = None
    project: str | None = None
    description: str | None = None
    operator: str | None = None
    last_error: str | None = None


class DocumentPageResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)


class SearchItem(BaseModel):
    chunk_id: UUID
    document_id: UUID
    score: float
    content: str
    file_url: str
    title: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]


class ChunkResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    file_url: str
    title: str | None
    start_line: int | None
    end_line: int | None
    metadata: dict[str, Any]
