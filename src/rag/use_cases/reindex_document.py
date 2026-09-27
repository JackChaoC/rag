from __future__ import annotations

import hashlib
from dataclasses import replace
from uuid import UUID

from rag.services.common.errors import DependencyError, NotFoundError
from rag.services.document_processing.document_processing_service import (
    DocumentProcessingService,
)
from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus
from rag.services.documents.types.document_summary import DocumentSummary
from rag.services.indexing.index_task_service import IndexTaskService
from rag.services.indexing.types.message import IndexMessage, IndexOperation


class ReindexDocument:
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
        self, document_id: UUID, data: bytes | None = None
    ) -> DocumentSummary:
        current = await self._documents.get(document_id)
        if current is None:
            raise NotFoundError("document not found")
        if current.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
            raise RuntimeError("deleted document cannot be reindexed")
        content = current.content
        if data is not None:
            content = await self._processing.parse_and_clean(data, current.source_type)
        digest = hashlib.sha256(content.encode()).hexdigest()
        if digest == current.content_hash:
            if current.status in {DocumentStatus.PENDING, DocumentStatus.FAILED}:
                try:
                    await self._tasks.publish(
                        IndexMessage(
                            current.id,
                            IndexOperation.REINDEX,
                            current.current_version,
                        )
                    )
                except Exception as exc:
                    await self._documents.set_status(
                        current.id, DocumentStatus.FAILED, error=str(exc)
                    )
                    raise DependencyError(
                        "index task could not be confirmed by RabbitMQ"
                    ) from exc
            return self._documents.summarize(current)
        updated = replace(
            current,
            content=content,
            content_hash=digest,
            current_version=current.current_version + 1,
            status=DocumentStatus.PENDING,
        )
        await self._documents.add_version(
            updated, self._processing.build_chunks(updated)
        )
        try:
            await self._tasks.publish(
                IndexMessage(
                    updated.id, IndexOperation.REINDEX, updated.current_version
                )
            )
        except Exception as exc:
            await self._documents.set_status(
                updated.id, DocumentStatus.FAILED, error=str(exc)
            )
            raise DependencyError(
                "index task could not be confirmed by RabbitMQ"
            ) from exc
        return self._documents.summarize(updated)
