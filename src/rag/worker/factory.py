from dataclasses import dataclass

from rag.core.embedding.embedder import Embedder
from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository
from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.infrastructure.vector_store.repositories.vector_repository import VectorRepository
from rag.worker.dispatcher import IndexingDispatcher
from rag.worker.document_indexer import DocumentIndexer
from rag.worker.handlers import (
    DocumentDeleteHandler,
    DocumentIngestHandler,
    DocumentReindexHandler,
    FailureHandler,
    RebuildHandler,
)


@dataclass(frozen=True, slots=True)
class WorkerServices:
    dispatcher: IndexingDispatcher
    failure_handler: FailureHandler
    rebuild_handler: RebuildHandler


def create_worker_services(
    documents: DocumentRepository,
    chunks: ChunkRepository,
    embedder: Embedder,
    vectors: VectorRepository,
) -> WorkerServices:
    document_indexer = DocumentIndexer(documents, chunks, embedder, vectors)
    return WorkerServices(
        dispatcher=IndexingDispatcher(
            DocumentIngestHandler(document_indexer),
            DocumentReindexHandler(document_indexer),
            DocumentDeleteHandler(documents, chunks, vectors),
        ),
        failure_handler=FailureHandler(documents, chunks, vectors),
        rebuild_handler=RebuildHandler(documents, chunks, embedder, vectors),
    )
