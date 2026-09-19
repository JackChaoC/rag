from uuid import uuid4

import pytest

from rag.indexing import IndexingWorker
from rag.infrastructure.database.entities.chunk import Chunk
from rag.infrastructure.database.entities.document import Document, DocumentStatus, SourceType
from rag.infrastructure.messaging.models import IndexMessage, IndexOperation


class Documents:
    def __init__(self, document):
        self.document = document

    async def get(self, document_id):
        return self.document if document_id == self.document.id else None

    async def list(self):
        return [self.document]

    async def set_status(self, document_id, status, *, error=None, expected=None):
        if expected and self.document.status not in expected:
            return False
        self.document.status = status
        self.document.last_error = error
        return True

    async def activate_version(self, document_id, version):
        if version != self.document.current_version:
            raise RuntimeError("version changed")
        self.document.status = DocumentStatus.READY
        self.document.last_error = None

    async def mark_deleted(self, document_id):
        self.document.status = DocumentStatus.DELETED
        self.document.last_error = None


class Chunks:
    def __init__(self, chunks):
        self.chunks = chunks

    async def for_version(self, document_id, version):
        return [item for item in self.chunks if item.document_id == document_id and item.version == version]

    async def all_ids(self, document_id, *, exclude_version=None):
        return [
            item.id for item in self.chunks
            if item.document_id == document_id and (exclude_version is None or item.version != exclude_version)
        ]


class Embedder:
    async def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


class Vectors:
    def __init__(self):
        self.points = {}
        self.dimension = None

    async def ensure_collection(self, dimension):
        self.dimension = dimension

    async def upsert(self, records):
        self.points.update({record.id: record.vector for record in records})

    async def delete(self, ids):
        for point_id in ids:
            self.points.pop(point_id, None)


class ActivateFailsOnce(Documents):
    def __init__(self, document):
        super().__init__(document)
        self.failures = 1

    async def activate_version(self, document_id, version):
        if self.failures:
            self.failures -= 1
            raise RuntimeError("postgres switch failed")
        await super().activate_version(document_id, version)


def setup(status=DocumentStatus.PENDING):
    doc = Document(uuid4(), "doc.md", SourceType.MARKDOWN, "text", "hash", status=status)
    chunk = Chunk(uuid4(), doc.id, 1, 0, "text")
    documents, chunks, vectors = Documents(doc), Chunks([chunk]), Vectors()
    return doc, chunk, IndexingWorker(documents, chunks, Embedder(), vectors), vectors


@pytest.mark.asyncio
async def test_duplicate_ingest_converges_to_one_point() -> None:
    doc, chunk, worker, vectors = setup()
    message = IndexMessage(doc.id, IndexOperation.INGEST, 1)

    await worker.handle(message)
    await worker.handle(message)

    assert doc.status is DocumentStatus.READY
    assert vectors.points == {chunk.id: [1.0, 0.0]}


@pytest.mark.asyncio
async def test_stale_message_only_removes_stale_version_points() -> None:
    doc, stale_chunk, worker, vectors = setup(DocumentStatus.READY)
    doc.current_version = 2
    vectors.points[stale_chunk.id] = [1.0, 0.0]

    await worker.handle(IndexMessage(doc.id, IndexOperation.REINDEX, 1))

    assert vectors.points == {}
    assert doc.status is DocumentStatus.READY


@pytest.mark.asyncio
async def test_terminal_failure_cleans_target_points_and_records_error() -> None:
    doc, chunk, worker, vectors = setup(DocumentStatus.INDEXING)
    vectors.points[chunk.id] = [1.0, 0.0]

    await worker.fail(IndexMessage(doc.id, IndexOperation.INGEST, 1), RuntimeError("ollama down"))

    assert vectors.points == {}
    assert doc.status is DocumentStatus.FAILED
    assert doc.last_error == "ollama down"


@pytest.mark.asyncio
async def test_qdrant_success_then_postgres_failure_converges_on_retry() -> None:
    doc = Document(uuid4(), "doc.md", SourceType.MARKDOWN, "text", "hash")
    chunk = Chunk(uuid4(), doc.id, 1, 0, "text")
    documents = ActivateFailsOnce(doc)
    vectors = Vectors()
    worker = IndexingWorker(documents, Chunks([chunk]), Embedder(), vectors)
    message = IndexMessage(doc.id, IndexOperation.INGEST, 1)

    with pytest.raises(RuntimeError, match="postgres switch failed"):
        await worker.handle(message)
    assert doc.status is DocumentStatus.FAILED
    assert vectors.points == {chunk.id: [1.0, 0.0]}

    await worker.handle(message)

    assert doc.status is DocumentStatus.READY
    assert doc.last_error is None
    assert vectors.points == {chunk.id: [1.0, 0.0]}


@pytest.mark.asyncio
async def test_duplicate_delete_is_idempotent() -> None:
    doc, chunk, worker, vectors = setup(DocumentStatus.DELETING)
    vectors.points[chunk.id] = [1.0, 0.0]
    message = IndexMessage(doc.id, IndexOperation.DELETE, 1)

    await worker.handle(message)
    await worker.handle(message)

    assert vectors.points == {}
    assert doc.status is DocumentStatus.DELETED
