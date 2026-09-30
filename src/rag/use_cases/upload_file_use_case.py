import hashlib
from uuid import NAMESPACE_URL, uuid4, uuid5

from rag.services.common.errors import ConflictError, DependencyError
from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import Document, DocumentStatus
from rag.services.files.file_service import FileService
from rag.services.publisher.publish_ingestion_document_task_service import (
    PublishIngestionDocumentTaskService,
)
from rag.services.publisher.types.message import IndexMessage, IndexOperation


class UploadFileUseCase:
    def __init__(
        self,
        fileService: FileService,
        documentService: DocumentService,
        publishIngestionDocumentTaskService: PublishIngestionDocumentTaskService,
    ) -> None:
        self.fileService = fileService
        self.documentService = documentService
        self.publishIngestionDocumentTaskService = publishIngestionDocumentTaskService

    async def execute(self, data, source_uri, source_type, title=None, metadata=None):
        if not data:
            raise ValueError("file is empty")
        if source_type.value not in {"markdown", "text", "pdf"}:
            raise ValueError("unsupported source type")
        digest = hashlib.sha256(data).hexdigest()
        async with self.documentService.lock(uuid5(NAMESPACE_URL, source_uri)):
            existing = await self.documentService.get_by_source_uri(source_uri)
            if existing:
                async with self.documentService.lock(existing.id):
                    existing = await self.documentService.get(existing.id)
                    if existing.status in {
                        DocumentStatus.DELETING,
                        DocumentStatus.DELETED,
                    }:
                        raise ConflictError(
                            "document was deleted; use a new source_uri"
                        )
                    if existing.content_hash != digest:
                        raise ConflictError(
                            "source_uri already exists with different content; use reindex"
                        )
                    if existing.status in {
                        DocumentStatus.PENDING,
                        DocumentStatus.FAILED,
                    }:
                        await self._publish(existing)
                    return self.documentService.summarize(existing)
            documentId = uuid4()
            filePath = await self.fileService.store(documentId, 1, source_type, data)
            document = Document(
                documentId,
                source_uri,
                source_type,
                filePath,
                digest,
                title=title,
                metadata=metadata or {},
            )
            try:
                await self.documentService.create(document)
            except Exception:
                await self.fileService.delete(filePath)
                raise
            async with self.documentService.lock(document.id):
                await self._publish(document)
            return self.documentService.summarize(document)

    async def _publish(self, document):
        await self.documentService.set_status(document.id, DocumentStatus.PENDING)
        document.status = DocumentStatus.PENDING
        try:
            await self.publishIngestionDocumentTaskService.publish(
                IndexMessage(
                    document.id, IndexOperation.INGEST, document.current_version
                )
            )
        except Exception as exc:
            await self.documentService.set_status(
                document.id, DocumentStatus.FAILED, error=str(exc)
            )
            raise DependencyError(
                "index task could not be confirmed by RabbitMQ"
            ) from exc
