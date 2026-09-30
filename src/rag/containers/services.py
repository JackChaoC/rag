from dependency_injector import containers, providers

from rag.services.documents.document_service import DocumentService
from rag.services.embedding.embedding_service import EmbeddingService
from rag.services.files.file_service import FileService
from rag.services.health.health_service import HealthService
from rag.services.indexing.index_task_service import IndexTaskService
from rag.services.indexing.vector_service import VectorService
from rag.services.reading.reader_service import ReaderService
from rag.services.retrieval.chunk_lookup_service import ChunkLookupService
from rag.services.retrieval.vector_query_service import VectorQueryService
from rag.services.splitting.markdown_node_parser import MarkdownNodeParser
from rag.services.splitting.splitter_service import SplitterService


class Services(containers.DeclarativeContainer):
    config = providers.Configuration()
    repositories = providers.DependenciesContainer()

    documentService = providers.Singleton(
        DocumentService, documentRepository=repositories.documentRepository
    )
    fileService = providers.Singleton(
        FileService, fileRepository=repositories.fileRepository
    )
    readerService = providers.Singleton(ReaderService)
    markdownNodeParser = providers.Factory(MarkdownNodeParser)
    splitterService = providers.Factory(
        SplitterService, markdownNodeParser=markdownNodeParser
    )
    embeddingService = providers.Singleton(
        EmbeddingService, embeddingRepository=repositories.embeddingRepository
    )
    vectorService = providers.Singleton(
        VectorService, vectorRepository=repositories.vectorRepository
    )
    chunkLookupService = providers.Singleton(
        ChunkLookupService, vectorRepository=repositories.vectorRepository
    )
    vectorQueryService = providers.Singleton(
        VectorQueryService, vectorRepository=repositories.vectorRepository
    )
    indexTaskService = providers.Singleton(
        IndexTaskService, indexTaskRepository=repositories.indexTaskRepository
    )
    healthService = providers.Singleton(
        HealthService, healthRepository=repositories.healthRepository
    )
