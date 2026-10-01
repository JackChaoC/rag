from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus
from rag.services.embedding.embedding_service import EmbeddingService
from rag.services.files.file_service import FileService
from rag.services.reading.reader_service import ReaderService
from rag.services.splitting.splitter_service import SplitterService
from rag.services.vector.vector_service import VectorService


class IndexDocumentUseCase:
    def __init__(
        self,
        documentService: DocumentService,
        fileService: FileService,
        readerService: ReaderService,
        splitterService: SplitterService,
        embeddingService: EmbeddingService,
        vectorService: VectorService,
    ) -> None:
        self.documentService = documentService
        self.fileService = fileService
        self.readerService = readerService
        self.splitterService = splitterService
        self.embeddingService = embeddingService
        self.vectorService = vectorService

    async def execute(self, message):
        async with self.documentService.lock(message.document_id):
            document = await self.documentService.get(message.document_id)
            if document is None:
                raise LookupError("document not found")
            if message.version < document.current_version:
                return
            if message.version > document.current_version:
                raise RuntimeError("message version is newer than document")
            if document.status in {DocumentStatus.DELETING, DocumentStatus.DELETED}:
                return
            await self.documentService.set_status(document.id, DocumentStatus.INDEXING)
            try:
                await self.vectorService.deleteDocument(document.id)
                metadata = dict(document.metadata)
                metadata.update(
                    document_id=str(document.id),
                    version=document.current_version,
                    source_uri=document.source_uri,
                    title=document.title or "",
                )
                llamaindex_documents = await self.readerService.read(
                    self.fileService.path(document.file_path), document.id, metadata
                )
                nodes = self.splitterService.split(llamaindex_documents)
                if not nodes:
                    raise ValueError("document has no chunks")
                nodes = await self.embeddingService.embedNodes(nodes)
                await self.vectorService.add(nodes)
                await self.documentService.set_status(document.id, DocumentStatus.READY)
            except Exception as exc:
                await self.documentService.set_status(
                    document.id, DocumentStatus.FAILED, error=str(exc)[:4000]
                )
                raise
