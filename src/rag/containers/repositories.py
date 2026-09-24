from dependency_injector import containers, providers

from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository
from rag.infrastructure.database.repositories.document_repository import (
    DocumentRepository,
)
from rag.infrastructure.vector_store.repositories.vector_repository import (
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
