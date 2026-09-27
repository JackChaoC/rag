from dependency_injector import containers, providers

from rag.worker.dispatcher import IndexingDispatcher
from rag.worker.handlers import (
    DocumentDeleteHandler,
    DocumentIngestHandler,
    DocumentReindexHandler,
    FailureHandler,
    RebuildHandler,
)


class Worker(containers.DeclarativeContainer):
    use_cases = providers.DependenciesContainer()

    document_ingest_handler = providers.Singleton(
        DocumentIngestHandler, index_document=use_cases.index_document
    )
    document_reindex_handler = providers.Singleton(
        DocumentReindexHandler, index_document=use_cases.index_document
    )
    document_delete_handler = providers.Singleton(
        DocumentDeleteHandler,
        delete_document_index=use_cases.delete_document_index,
    )
    dispatcher = providers.Singleton(
        IndexingDispatcher,
        document_ingest_handler=document_ingest_handler,
        document_reindex_handler=document_reindex_handler,
        document_delete_handler=document_delete_handler,
    )
    failure_handler = providers.Singleton(
        FailureHandler,
        finalize_index_failure=use_cases.finalize_index_failure,
    )
    rebuild_handler = providers.Singleton(
        RebuildHandler,
        rebuild_index=use_cases.rebuild_index,
    )
