from dependency_injector import containers, providers

from rag.services.document_processing.document_processing_service import (
    DocumentProcessingService,
)
from rag.services.document_processing.parser import DocumentParser
from rag.services.documents.chunk_service import ChunkService
from rag.services.documents.document_service import DocumentService
from rag.services.embedding.embedding_service import EmbeddingService
from rag.services.health.health_service import HealthService
from rag.services.indexing.index_task_service import IndexTaskService
from rag.services.indexing.vector_service import VectorService
from rag.services.retrieval.vector_search import VectorSearch


class Services(containers.DeclarativeContainer):
    config = providers.Configuration()
    repositories = providers.DependenciesContainer()

    # MarkItDown runs in worker threads; do not share parser instances.
    parser = providers.Factory(DocumentParser)
    document_processing = providers.Factory(DocumentProcessingService, parser=parser)
    documents = providers.Singleton(DocumentService, documents=repositories.documents)
    chunks = providers.Singleton(ChunkService, chunks=repositories.chunks)
    embeddings = providers.Singleton(
        EmbeddingService, embeddings=repositories.embeddings
    )
    vectors = providers.Singleton(VectorService, vectors=repositories.vectors)
    index_tasks = providers.Singleton(IndexTaskService, tasks=repositories.tasks)
    health = providers.Singleton(
        HealthService,
        documents=repositories.documents,
        tasks=repositories.tasks,
        vectors=repositories.vectors,
        embeddings=repositories.embeddings,
    )
    vector_search = providers.Singleton(
        VectorSearch,
        embedder=embeddings,
        vectors=vectors,
        chunks=chunks,
        max_candidates=config.search_max_candidates,
    )
