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

    documentIngestHandler = providers.Singleton(
        DocumentIngestHandler, indexDocumentUseCase=use_cases.indexDocumentUseCase
    )
    documentReindexHandler = providers.Singleton(
        DocumentReindexHandler, indexDocumentUseCase=use_cases.indexDocumentUseCase
    )
    documentDeleteHandler = providers.Singleton(
        DocumentDeleteHandler,
        deleteDocumentIndexUseCase=use_cases.deleteDocumentIndexUseCase,
    )
    dispatcher = providers.Singleton(
        IndexingDispatcher,
        documentIngestHandler=documentIngestHandler,
        documentReindexHandler=documentReindexHandler,
        documentDeleteHandler=documentDeleteHandler,
    )
    failureHandler = providers.Singleton(
        FailureHandler,
        finalizeIndexFailureUseCase=use_cases.finalizeIndexFailureUseCase,
    )
    rebuildHandler = providers.Singleton(
        RebuildHandler,
        rebuildIndexUseCase=use_cases.rebuildIndexUseCase,
    )
