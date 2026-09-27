from dependency_injector import containers, providers

from rag.repositories.chunk_repository import ChunkRepository
from rag.repositories.document_repository import (
    DocumentRepository,
)
from rag.repositories.embedding_repository import EmbeddingRepository
from rag.repositories.health_repository import HealthRepository
from rag.repositories.index_task_repository import IndexTaskRepository
from rag.repositories.vector_repository import (
    VectorRepository,
)


class Repositories(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()

    sessions = resources.database.provided.require_session_factory.call()
    documents = providers.Singleton(DocumentRepository, sessions=sessions)
    chunks = providers.Singleton(ChunkRepository, sessions=sessions)
    vectors = providers.Singleton(
        VectorRepository, client=resources.qdrant, collection=config.qdrant_collection
    )
    embeddings = providers.Singleton(EmbeddingRepository, embedder=resources.embedder)
    index_tasks = providers.Singleton(IndexTaskRepository, broker=resources.broker)
    health = providers.Singleton(
        HealthRepository,
        database=resources.database,
        broker=resources.broker,
        qdrant=resources.qdrant,
        http_client_factory=resources.health_http_client.provider,
    )
