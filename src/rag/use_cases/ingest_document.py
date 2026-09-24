from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from uuid import uuid4

from rag.core.document_processing.chunker import chunk_markdown
from rag.core.document_processing.cleaner import clean_markdown
from rag.core.document_processing.parser import DocumentParser
from rag.infrastructure.database.entities.chunk import Chunk
from rag.infrastructure.database.entities.document import Document, DocumentStatus, SourceType
from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.infrastructure.messaging.models import IndexMessage, IndexOperation
from rag.use_cases.common import ConflictError, DependencyError, DocumentSummary


class IngestDocument:
    def __init__(
        self, parser: DocumentParser, documents: DocumentRepository,
        publish: Callable[[IndexMessage], Awaitable[None]],
    ) -> None:
        self._parser = parser
        self._documents = documents
        self._publish = publish

    async def execute(
        self, data: bytes, source_uri: str, source_type: SourceType,
        title: str | None = None, metadata: dict | None = None,
    ) -> DocumentSummary:
        parsed = await self._parser.parse(data, source_type)
        content = clean_markdown(parsed.markdown)
        if not content:
            raise ValueError("parsed document is empty")
        digest = hashlib.sha256(content.encode()).hexdigest()
        existing = await self._documents.get_by_source_uri(source_uri) #todo: check source_uri before parse data
        if existing:
            if existing.content_hash != digest:
                raise ConflictError("source_uri already exists with different content; use reindex")
            if existing.status in {DocumentStatus.PENDING, DocumentStatus.FAILED}:
                await self._publish(IndexMessage(existing.id, IndexOperation.INGEST, existing.current_version))
            return _summary(existing)

        document = Document(
            uuid4(), source_uri, source_type, content, digest, title=title,
            metadata=metadata or {}, status=DocumentStatus.PENDING,
        )
        chunks = _make_chunks(document)
        await self._documents.create_with_chunks(document, chunks)
        try:
            await self._publish(IndexMessage(document.id, IndexOperation.INGEST, 1))
        except Exception as exc:
            await self._documents.set_status(document.id, DocumentStatus.FAILED, error=str(exc))
            raise DependencyError("index task could not be confirmed by RabbitMQ") from exc
        return _summary(document)


def _make_chunks(document: Document) -> list[Chunk]:
    return [
        Chunk(uuid4(), document.id, document.current_version, draft.chunk_index, draft.content,
              draft.start_line, draft.end_line, draft.token_count, draft.metadata)
        for draft in chunk_markdown(document.content)
    ]


def _summary(document: Document) -> DocumentSummary:
    return DocumentSummary(document.id, document.source_uri, document.title, document.current_version,
                           document.status, document.metadata)
