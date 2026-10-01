import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from dependency_injector import providers
from llama_index.core.embeddings import MockEmbedding
from qdrant_client import AsyncQdrantClient

from rag.config import Settings
from rag.containers import create_container


class MemoryDocumentRepository:
    def __init__(self):
        self.documents = {}
        self.locks = {}

    @asynccontextmanager
    async def lock(self, key):
        async with self.locks.setdefault(key, asyncio.Lock()):
            yield

    async def get(self, documentId):
        return self.documents.get(documentId)

    async def get_by_source_uri(self, uri):
        return next((d for d in self.documents.values() if d.source_uri == uri), None)

    async def list(self):
        return list(self.documents.values())

    async def create(self, document):
        self.documents[document.id] = document

    async def save(self, document):
        self.documents[document.id] = document

    async def set_status(self, documentId, status, *, error=None, expected=None):
        document = self.documents[documentId]
        if expected and document.status not in expected:
            return False
        document.status, document.last_error = status, error
        return True


@pytest.fixture
async def appContainer(tmp_path):
    container = create_container(Settings(_env_file=None, storage_path=str(tmp_path)))
    client = AsyncQdrantClient(location=":memory:")
    documents = MemoryDocumentRepository()
    container.repositories.documentRepository.override(providers.Object(documents))
    container.resources.qdrantResource.override(providers.Object(client))
    container.resources.ollamaResource.override(
        providers.Object(MockEmbedding(embed_dim=8))
    )
    container.resources.rabbitmqResource.override(
        providers.Object(SimpleNamespace(publish=AsyncMock()))
    )
    try:
        yield container
    finally:
        container.unwire()
        container.reset_singletons()
        await client.close()
