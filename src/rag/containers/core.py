from dependency_injector import containers, providers

from rag.core.document_processing.parser import DocumentParser
from rag.core.retrieval.vector_search import VectorSearch


class Core(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()
    repositories = providers.DependenciesContainer()

    # MarkItDown runs in worker threads; do not share parser instances.
    parser = providers.Factory(DocumentParser)
    vector_search = providers.Singleton(
        VectorSearch,
        embedder=resources.embedder,
        vectors=repositories.vectors,
        chunks=repositories.chunks,
        max_candidates=config.search_max_candidates,
    )
