from dependency_injector import containers, providers

from rag.worker.dispatcher import IndexingDispatcher
from rag.worker.document_indexer import DocumentIndexer
from rag.worker.handlers import (
    DocumentDeleteHandler,
    DocumentIngestHandler,
    DocumentReindexHandler,
    FailureHandler,
    RebuildHandler,
)


class Worker(containers.DeclarativeContainer):
    resources = providers.DependenciesContainer()
    repositories = providers.DependenciesContainer()

    document_indexer = providers.Singleton(
        DocumentIndexer,
        documents=repositories.documents,
        chunks=repositories.chunks,
        embedder=resources.embedder,
        vectors=repositories.vectors,
    )
    document_ingest_handler = providers.Singleton(
        DocumentIngestHandler, indexer=document_indexer
    )
    document_reindex_handler = providers.Singleton(
        DocumentReindexHandler, indexer=document_indexer
    )
    document_delete_handler = providers.Singleton(
        DocumentDeleteHandler,
        documents=repositories.documents,
        chunks=repositories.chunks,
        vectors=repositories.vectors,
    )
    dispatcher = providers.Singleton(
        IndexingDispatcher,
        document_ingest_handler=document_ingest_handler,
        document_reindex_handler=document_reindex_handler,
        document_delete_handler=document_delete_handler,
    )
    failure_handler = providers.Singleton(
        FailureHandler,
        documents=repositories.documents,
        chunks=repositories.chunks,
        vectors=repositories.vectors,
    )
    rebuild_handler = providers.Singleton(
        RebuildHandler,
        documents=repositories.documents,
        chunks=repositories.chunks,
        embedder=resources.embedder,
        vectors=repositories.vectors,
    )
