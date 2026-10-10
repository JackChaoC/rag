from dataclasses import replace

from rag.services.common.errors import DependencyError, NotFoundError
from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus
from rag.services.files.file_service import FileService
from rag.services.publisher.publish_ingestion_document_task_service import (
    PublishIngestionDocumentTaskService,
)
from rag.services.publisher.types.message import IndexMessage, IndexOperation
from rag.services.vector.vector_service import VectorService


class ReindexDocumentUseCase:
    def __init__(
        self,
        fileService: FileService,
        documentService: DocumentService,
        vectorService: VectorService,
        publishIngestionDocumentTaskService: PublishIngestionDocumentTaskService,
    ) -> None:
        self.fileService = fileService
        self.documentService = documentService
        self.vectorService = vectorService
        self.publishIngestionDocumentTaskService = publishIngestionDocumentTaskService

    async def execute(self, documentId, file_url=None):
        async with self.documentService.lock(documentId):
            current = await self.documentService.get(documentId)
            if current is None:
                raise NotFoundError("document not found")
            if current.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
                raise ValueError("deleted document cannot be reindexed")
            file = await self.fileService.fromUrl(file_url) if file_url else await self.fileService.get(current.file_id)
            version = current.current_version + 1
            updated = replace(
                current,
                file_id=file.id,
                file_path=file.file_path,
                source_type=file.source_type,
                content_hash=file.content_hash,
                current_version=version,
                status=DocumentStatus.PENDING,
                last_error=None,
            )
            await self.documentService.save(updated)
            try:
                await self.vectorService.deleteDocument(documentId)
                await self.publishIngestionDocumentTaskService.publish(
                    IndexMessage(documentId, IndexOperation.REINDEX, version)
                )
            except Exception as exc:
                await self.documentService.set_status(
                    documentId, DocumentStatus.FAILED, error=str(exc)
                )
                raise DependencyError(
                    "reindex could not be completed or queued"
                ) from exc
            return self.documentService.summarize(updated)
