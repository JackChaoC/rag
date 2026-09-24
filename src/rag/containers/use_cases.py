from dependency_injector import containers, providers

from rag.use_cases.check_health import CheckHealth
from rag.use_cases.delete_document import DeleteDocument
from rag.use_cases.get_document_chunk import GetDocumentChunk
from rag.use_cases.ingest_document import IngestDocument
from rag.use_cases.list_documents import ListDocuments
from rag.use_cases.reindex_document import ReindexDocument
from rag.use_cases.search_knowledge import SearchKnowledge


class UseCases(containers.DeclarativeContainer):
    resources = providers.DependenciesContainer()
    repositories = providers.DependenciesContainer()
    core = providers.DependenciesContainer()

    # Parser owners must remain factories to avoid retaining a shared parser.
    ingest_document = providers.Factory(
        IngestDocument,
        parser=core.parser,
        documents=repositories.documents,
        publish=resources.broker.provided.publish,
    )
    reindex_document = providers.Factory(
        ReindexDocument,
        parser=core.parser,
        documents=repositories.documents,
        publish=resources.broker.provided.publish,
    )
    delete_document = providers.Singleton(
        DeleteDocument,
        documents=repositories.documents,
        publish=resources.broker.provided.publish,
    )
    list_documents = providers.Singleton(
        ListDocuments, documents=repositories.documents
    )
    get_document_chunk = providers.Singleton(
        GetDocumentChunk, chunks=repositories.chunks
    )
    search_knowledge = providers.Singleton(SearchKnowledge, search=core.vector_search)
    check_health = providers.Singleton(
        CheckHealth,
        database=resources.database,
        broker=resources.broker,
        qdrant=resources.qdrant,
        http_client_factory=resources.health_http_client.provider,
    )
