from __future__ import annotations

from qdrant_client import AsyncQdrantClient

from rag.config import Settings
from rag.core.document_processing.parser import DocumentParser
from rag.core.retrieval.vector_search import VectorSearch
from rag.infrastructure.database.client import Database
from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository
from rag.infrastructure.database.repositories.document_repository import DocumentRepository
from rag.infrastructure.embedding.ollama_embedder import OllamaEmbedder
from rag.infrastructure.messaging.broker import RabbitBroker
from rag.infrastructure.vector_store.repositories.vector_repository import VectorRepository
from rag.use_cases.delete_document import DeleteDocument
from rag.use_cases.get_document_chunk import GetDocumentChunk
from rag.use_cases.ingest_document import IngestDocument
from rag.use_cases.list_documents import ListDocuments
from rag.use_cases.reindex_document import ReindexDocument
from rag.use_cases.search_knowledge import SearchKnowledge


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.database = Database(settings.database_url)
        self.broker = RabbitBroker(settings.rabbitmq_url, settings.rabbitmq_retry_delays, settings.rabbitmq_prefetch)
        self.qdrant = AsyncQdrantClient(url=settings.qdrant_url)
        self.embedder = OllamaEmbedder(
            settings.ollama_url, settings.embedding_model, num_gpu=settings.ollama_num_gpu,
        )

    async def start(self) -> None:
        await self.database.connect()
        await self.broker.connect()
        sessions = self.database.require_session_factory()
        self.documents = DocumentRepository(sessions)
        self.chunks = ChunkRepository(sessions)
        self.vectors = VectorRepository(self.qdrant, self.settings.qdrant_collection)
        parser = DocumentParser()
        self.ingest = IngestDocument(parser, self.documents, self.broker.publish)
        self.reindex = ReindexDocument(parser, self.documents, self.broker.publish)
        self.delete = DeleteDocument(self.documents, self.broker.publish)
        self.list_documents = ListDocuments(self.documents)
        self.get_chunk = GetDocumentChunk(self.chunks)
        self.search = SearchKnowledge(VectorSearch(
            self.embedder, self.vectors, self.chunks, self.settings.search_max_candidates,
        ))

    async def close(self) -> None:
        await self.broker.close()
        await self.embedder.aclose()
        await self.qdrant.close()
        await self.database.close()
