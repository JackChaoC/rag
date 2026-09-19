from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import replace
from uuid import UUID

from rag.core.document_processing.cleaner import clean_markdown
from rag.core.document_processing.parser import DocumentParser
from rag.infrastructure.database.entities.document import DocumentStatus
from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.infrastructure.messaging.models import IndexMessage, IndexOperation
from rag.use_cases.common import DependencyError, DocumentSummary, NotFoundError
from rag.use_cases.ingest_document import _make_chunks, _summary


class ReindexDocument:
    def __init__(
        self, parser: DocumentParser, documents: DocumentRepository,
        publish: Callable[[IndexMessage], Awaitable[None]],
    ) -> None:
        self._parser = parser
        self._documents = documents
        self._publish = publish

    async def execute(self, document_id: UUID, data: bytes | None = None) -> DocumentSummary:
        current = await self._documents.get(document_id)
        if current is None:
            raise NotFoundError("document not found")
        if current.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
            raise RuntimeError("deleted document cannot be reindexed")
        content = current.content
        if data is not None:
            parsed = await self._parser.parse(data, current.source_type)
            content = clean_markdown(parsed.markdown)
            if not content:
                raise ValueError("parsed document is empty")
        digest = hashlib.sha256(content.encode()).hexdigest()
        if digest == current.content_hash:
            if current.status in {DocumentStatus.PENDING, DocumentStatus.FAILED}:
                try:
                    await self._publish(IndexMessage(current.id, IndexOperation.REINDEX, current.current_version))
                except Exception as exc:
                    await self._documents.set_status(current.id, DocumentStatus.FAILED, error=str(exc))
                    raise DependencyError("index task could not be confirmed by RabbitMQ") from exc
            return _summary(current)
        updated = replace(
            current, content=content, content_hash=digest,
            current_version=current.current_version + 1, status=DocumentStatus.PENDING,
        )
        await self._documents.add_version(updated, _make_chunks(updated))
        try:
            await self._publish(IndexMessage(updated.id, IndexOperation.REINDEX, updated.current_version))
        except Exception as exc:
            await self._documents.set_status(updated.id, DocumentStatus.FAILED, error=str(exc))
            raise DependencyError("index task could not be confirmed by RabbitMQ") from exc
        return _summary(updated)
