from dependency_injector import containers, providers

from rag.repositories.chunk_repository import ChunkRepository
from rag.repositories.document_repository import (
    DocumentRepository,
)
from rag.repositories.embedding_repository import EmbeddingRepository
from rag.repositories.task_repository import TaskRepository
from rag.repositories.vector_repository import (
    VectorRepository,
)


class Repositories(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()

    sessions = resources.postgresql.provided.require_session_factory.call()
    documents = providers.Singleton(DocumentRepository, sessions=sessions)
    chunks = providers.Singleton(ChunkRepository, sessions=sessions)
    vectors = providers.Singleton(
        VectorRepository, client=resources.qdrant, collection=config.qdrant_collection
    )
    embeddings = providers.Singleton(EmbeddingRepository, embedder=resources.ollama)
    tasks = providers.Singleton(TaskRepository, broker=resources.rabbitmq)
