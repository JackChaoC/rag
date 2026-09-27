from dependency_injector import containers, providers

from rag.use_cases.check_health import CheckHealth
from rag.use_cases.delete_document import DeleteDocument
from rag.use_cases.delete_document_index import DeleteDocumentIndex
from rag.use_cases.finalize_index_failure import FinalizeIndexFailure
from rag.use_cases.get_document_chunk import GetDocumentChunk
from rag.use_cases.index_document import IndexDocument
from rag.use_cases.ingest_document import IngestDocument
from rag.use_cases.list_documents import ListDocuments
from rag.use_cases.rebuild_index import RebuildIndex
from rag.use_cases.reindex_document import ReindexDocument
from rag.use_cases.search_knowledge import SearchKnowledge


class UseCases(containers.DeclarativeContainer):
    services = providers.DependenciesContainer()

    # Parser owners must remain factories to avoid retaining a shared parser.
    ingest_document = providers.Factory(
        IngestDocument,
        processing=services.document_processing,
        documents=services.documents,
        tasks=services.index_tasks,
    )
    reindex_document = providers.Factory(
        ReindexDocument,
        processing=services.document_processing,
        documents=services.documents,
        tasks=services.index_tasks,
    )
    delete_document = providers.Singleton(
        DeleteDocument,
        documents=services.documents,
        tasks=services.index_tasks,
    )
    list_documents = providers.Singleton(ListDocuments, documents=services.documents)
    get_document_chunk = providers.Singleton(GetDocumentChunk, chunks=services.chunks)
    search_knowledge = providers.Singleton(
        SearchKnowledge, search=services.vector_search
    )
    check_health = providers.Singleton(CheckHealth, health=services.health)
    index_document = providers.Singleton(
        IndexDocument,
        documents=services.documents,
        chunks=services.chunks,
        embedder=services.embeddings,
        vectors=services.vectors,
    )
    delete_document_index = providers.Singleton(
        DeleteDocumentIndex,
        documents=services.documents,
        chunks=services.chunks,
        vectors=services.vectors,
    )
    finalize_index_failure = providers.Singleton(
        FinalizeIndexFailure,
        documents=services.documents,
        chunks=services.chunks,
        vectors=services.vectors,
    )
    rebuild_index = providers.Singleton(
        RebuildIndex,
        documents=services.documents,
        chunks=services.chunks,
        embedder=services.embeddings,
        vectors=services.vectors,
    )
