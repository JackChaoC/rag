from dependency_injector import containers, providers

from rag.repositories.document_repository import DocumentRepository
from rag.repositories.embedding_repository import EmbeddingRepository
from rag.repositories.file_repository import FileRepository
from rag.repositories.health_repository import HealthRepository
from rag.repositories.index_task_repository import IndexTaskRepository
from rag.repositories.vector_repository import VectorRepository


class Repositories(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()

    documentRepository = providers.Singleton(
        DocumentRepository,
        sessions=resources.databaseResource.provided.require_session_factory.call(),
        lockEngine=resources.databaseResource.provided.lockEngine,
    )
    fileRepository = providers.Singleton(FileRepository, root=config.storage_path)
    vectorRepository = providers.Singleton(
        VectorRepository,
        qdrantResource=resources.qdrantResource,
        ollamaResource=resources.ollamaResource,
        collection=config.qdrant_collection,
    )
    embeddingRepository = providers.Singleton(
        EmbeddingRepository, ollamaResource=resources.ollamaResource
    )
    indexTaskRepository = providers.Singleton(
        IndexTaskRepository, brokerResource=resources.brokerResource
    )
    healthRepository = providers.Singleton(
        HealthRepository,
        databaseResource=resources.databaseResource,
        brokerResource=resources.brokerResource,
        qdrantResource=resources.qdrantResource,
        httpClientFactory=resources.healthHttpClientResource.provider,
    )
