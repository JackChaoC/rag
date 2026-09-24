import httpx
from dependency_injector import containers, providers

from rag.config import Settings, get_settings
from rag.core.document_processing.parser import DocumentParser
from rag.core.retrieval.vector_search import VectorSearch
from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository
from rag.infrastructure.database.repositories.document_repository import (
    DocumentRepository,
)
from rag.infrastructure.vector_store.repositories.vector_repository import (
    VectorRepository,
)
from rag.resources import (
    broker_resource,
    database_resource,
    embedder_resource,
    qdrant_resource,
)
from rag.use_cases.check_health import CheckHealth
from rag.use_cases.delete_document import DeleteDocument
from rag.use_cases.get_document_chunk import GetDocumentChunk
from rag.use_cases.ingest_document import IngestDocument
from rag.use_cases.list_documents import ListDocuments
from rag.use_cases.reindex_document import ReindexDocument
from rag.use_cases.search_knowledge import SearchKnowledge
from rag.worker.dispatcher import IndexingDispatcher
from rag.worker.document_indexer import DocumentIndexer
from rag.worker.handlers import (
    DocumentDeleteHandler,
    DocumentIngestHandler,
    DocumentReindexHandler,
    FailureHandler,
    RebuildHandler,
)


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    database = providers.Resource(database_resource, config.database_url)
    broker = providers.Resource(
        broker_resource,
        config.rabbitmq_url,
        config.rabbitmq_retry_delays,
        config.rabbitmq_prefetch,
    )
    qdrant = providers.Resource(qdrant_resource, config.qdrant_url)
    embedder = providers.Resource(
        embedder_resource,
        config.ollama_url,
        config.embedding_model,
        config.ollama_num_gpu,
    )
    sessions = database.provided.require_session_factory.call()
    documents = providers.Factory(DocumentRepository, sessions=sessions)
    chunks = providers.Factory(ChunkRepository, sessions=sessions)
    vectors = providers.Factory(
        VectorRepository, client=qdrant, collection=config.qdrant_collection
    )
    parser = providers.Factory(DocumentParser)
    ingest_document = providers.Factory(
        IngestDocument,
        parser=parser,
        documents=documents,
        publish=broker.provided.publish,
    )
    reindex_document = providers.Factory(
        ReindexDocument,
        parser=parser,
        documents=documents,
        publish=broker.provided.publish,
    )
    delete_document = providers.Factory(
        DeleteDocument, documents=documents, publish=broker.provided.publish
    )
    list_documents = providers.Factory(ListDocuments, documents=documents)
    get_document_chunk = providers.Factory(GetDocumentChunk, chunks=chunks)
    vector_search = providers.Factory(
        VectorSearch,
        embedder=embedder,
        vectors=vectors,
        chunks=chunks,
        max_candidates=config.search_max_candidates,
    )
    search_knowledge = providers.Factory(SearchKnowledge, search=vector_search)
    health_http_client = providers.Factory(
        httpx.AsyncClient,
        base_url=config.ollama_url,
        timeout=2,
    )
    check_health = providers.Factory(
        CheckHealth,
        database=database,
        broker=broker,
        qdrant=qdrant,
        http_client_factory=health_http_client.provider,
    )
    document_indexer = providers.Factory(
        DocumentIndexer,
        documents=documents,
        chunks=chunks,
        embedder=embedder,
        vectors=vectors,
    )
    document_ingest_handler = providers.Factory(
        DocumentIngestHandler, indexer=document_indexer
    )
    document_reindex_handler = providers.Factory(
        DocumentReindexHandler, indexer=document_indexer
    )
    document_delete_handler = providers.Factory(
        DocumentDeleteHandler,
        documents=documents,
        chunks=chunks,
        vectors=vectors,
    )
    dispatcher = providers.Factory(
        IndexingDispatcher,
        document_ingest_handler=document_ingest_handler,
        document_reindex_handler=document_reindex_handler,
        document_delete_handler=document_delete_handler,
    )
    failure_handler = providers.Factory(
        FailureHandler, documents=documents, chunks=chunks, vectors=vectors
    )
    rebuild_handler = providers.Factory(
        RebuildHandler,
        documents=documents,
        chunks=chunks,
        embedder=embedder,
        vectors=vectors,
    )


def create_container(settings: Settings | None = None) -> Container:
    container = Container()
    container.config.from_dict((settings or get_settings()).model_dump())
    return container
