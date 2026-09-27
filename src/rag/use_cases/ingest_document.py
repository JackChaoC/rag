from __future__ import annotations

import hashlib
from uuid import uuid4

from rag.services.common.errors import ConflictError, DependencyError
from rag.services.document_processing.document_processing_service import (
    DocumentProcessingService,
)
from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import (
    Document,
    DocumentStatus,
    SourceType,
)
from rag.services.documents.types.document_summary import DocumentSummary
from rag.services.indexing.index_task_service import IndexTaskService
from rag.services.indexing.types.message import IndexMessage, IndexOperation


class IngestDocument:
    def __init__(
        self,
        processing: DocumentProcessingService,
        documents: DocumentService,
        tasks: IndexTaskService,
    ) -> None:
        self._processing = processing
        self._documents = documents
        self._tasks = tasks

    async def execute(
        self,
        data: bytes,
        source_uri: str,
        source_type: SourceType,
        title: str | None = None,
        metadata: dict | None = None,
    ) -> DocumentSummary:
        content = await self._processing.parse_and_clean(data, source_type)
        digest = hashlib.sha256(content.encode()).hexdigest()
        existing = await self._documents.get_by_source_uri(
            source_uri
        )  # todo: check source_uri before parse data
        if existing:
            if existing.content_hash != digest:
                raise ConflictError(
                    "source_uri already exists with different content; use reindex"
                )
            if existing.status in {DocumentStatus.PENDING, DocumentStatus.FAILED}:
                await self._tasks.publish(
                    IndexMessage(
                        existing.id, IndexOperation.INGEST, existing.current_version
                    )
                )
            return self._documents.summarize(existing)

        document = Document(
            uuid4(),
            source_uri,
            source_type,
            content,
            digest,
            title=title,
            metadata=metadata or {},
            status=DocumentStatus.PENDING,
        )
        chunks = self._processing.build_chunks(document)
        await self._documents.create_with_chunks(document, chunks)
        try:
            await self._tasks.publish(
                IndexMessage(document.id, IndexOperation.INGEST, 1)
            )
        except Exception as exc:
            await self._documents.set_status(
                document.id, DocumentStatus.FAILED, error=str(exc)
            )
            raise DependencyError(
                "index task could not be confirmed by RabbitMQ"
            ) from exc
        return self._documents.summarize(document)
