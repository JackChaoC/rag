from dependency_injector import containers, providers

from rag.repositories.document_repository import DocumentRepository
from rag.repositories.embedding_repository import EmbeddingRepository
from rag.repositories.file_repository import FileRepository
from rag.repositories.file_record_repository import FileRecordRepository
from rag.repositories.task_repository import TaskRepository
from rag.repositories.vector_repository import VectorRepository


class Repositories(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()

    documentRepository = providers.Singleton(
        DocumentRepository,
        sessions=resources.postgresqlResource.provided.require_session_factory.call(),
        lockEngine=resources.postgresqlResource.provided.lockEngine,
    )
    fileRecordRepository = providers.Singleton(
        FileRecordRepository,
        sessions=resources.postgresqlResource.provided.require_session_factory.call(),
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
    taskRepository = providers.Singleton(
        TaskRepository, rabbitmqResource=resources.rabbitmqResource
    )
