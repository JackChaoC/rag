from uuid import NAMESPACE_URL, uuid4, uuid5

from rag.services.common.errors import ConflictError, DependencyError
from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import Document, DocumentStatus, Team
from rag.services.files.file_service import FileService
from rag.services.publisher.publish_ingestion_document_task_service import PublishIngestionDocumentTaskService
from rag.services.publisher.types.message import IndexMessage, IndexOperation


class IngestDocumentUseCase:
    def __init__(self, fileService: FileService, documentService: DocumentService,
                 publishIngestionDocumentTaskService: PublishIngestionDocumentTaskService):
        self.fileService = fileService
        self.documentService = documentService
        self.publishIngestionDocumentTaskService = publishIngestionDocumentTaskService

    async def execute(self, file_url, title, team=None, project=None, description=None, operator=None, metadata=None):
        title = title.strip()
        if not title:
            raise ValueError("title is required")
        team = Team(team) if team is not None else None
        file = await self.fileService.fromUrl(file_url)
        fileLockId = uuid5(NAMESPACE_URL, f"rag:file:{file.id}")
        async with self.documentService.lock(fileLockId):
            existing = await self.documentService.get_by_file_id(file.id)
            if existing:
                async with self.documentService.lock(existing.id):
                    existing = await self.documentService.get(existing.id)
                    if existing.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
                        raise ConflictError("document was deleted; upload a new file")
                    if (existing.title, existing.team, existing.project, existing.description, existing.operator, existing.metadata) != (title, team, project, description, operator, metadata or {}):
                        raise ConflictError("file already belongs to a document with different information")
                    if existing.status in {DocumentStatus.PENDING, DocumentStatus.FAILED}:
                        await self._publish(existing)
                    return self.documentService.summarize(existing)
            document = Document(id=uuid4(), file_id=file.id, title=title, source_type=file.source_type,
                                file_path=file.file_path, content_hash=file.content_hash, team=team,
                                project=project, description=description, operator=operator, metadata=metadata or {})
            await self.documentService.create(document)
            async with self.documentService.lock(document.id):
                await self._publish(document)
            return self.documentService.summarize(document)

    async def _publish(self, document):
        await self.documentService.set_status(document.id, DocumentStatus.PENDING)
        document.status = DocumentStatus.PENDING
        try:
            await self.publishIngestionDocumentTaskService.publish(
                IndexMessage(document.id, IndexOperation.INGEST, document.current_version))
        except Exception as exc:
            await self.documentService.set_status(document.id, DocumentStatus.FAILED, error=str(exc))
            raise DependencyError("index task could not be confirmed by RabbitMQ") from exc
