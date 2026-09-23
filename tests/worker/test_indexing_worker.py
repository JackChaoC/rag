from uuid import uuid4

import pytest

from rag.infrastructure.database.entities.chunk import Chunk
from rag.infrastructure.database.entities.document import Document, DocumentStatus, SourceType
from rag.infrastructure.messaging.models import IndexMessage, IndexOperation
from rag.worker.dispatcher import IndexingDispatcher
from rag.worker.factory import create_worker_services


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
    def __init__(self):
        self.texts = []

    async def embed(self, texts):
        self.texts.extend(texts)
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


class RecordingHandler:
    def __init__(self) -> None:
        self.messages = []

    async def handle(self, message) -> None:
        self.messages.append(message)


def setup(status=DocumentStatus.PENDING):
    doc = Document(uuid4(), "doc.md", SourceType.MARKDOWN, "text", "hash", status=status)
    chunk = Chunk(uuid4(), doc.id, 1, 0, "text")
    documents, chunks, vectors = Documents(doc), Chunks([chunk]), Vectors()
    services = create_worker_services(documents, chunks, Embedder(), vectors)
    return doc, chunk, services, vectors


@pytest.mark.asyncio
async def test_worker_embeds_document_title_heading_and_body() -> None:
    doc = Document(
        uuid4(), "doc.md", SourceType.MARKDOWN, "text", "hash",
        title="Database Guide",
    )
    chunk = Chunk(
        uuid4(), doc.id, 1, 0, "## Migration\nAlembic manages revisions.",
        metadata={"heading": "Migration"},
    )
    embedder = Embedder()
    services = create_worker_services(Documents(doc), Chunks([chunk]), embedder, Vectors())
    message = IndexMessage(doc.id, IndexOperation.INGEST, 1)

    await services.dispatcher.dispatch(message.operation.routing_key, message)

    assert embedder.texts == [
        "# Database Guide\n\n## Migration\n\nAlembic manages revisions."
    ]


@pytest.mark.asyncio
async def test_duplicate_ingest_converges_to_one_point() -> None:
    doc, chunk, services, vectors = setup()
    message = IndexMessage(doc.id, IndexOperation.INGEST, 1)

    await services.dispatcher.dispatch(message.operation.routing_key, message)
    await services.dispatcher.dispatch(message.operation.routing_key, message)

    assert doc.status is DocumentStatus.READY
    assert vectors.points == {chunk.id: [1.0, 0.0]}


@pytest.mark.asyncio
async def test_stale_message_only_removes_stale_version_points() -> None:
    doc, stale_chunk, services, vectors = setup(DocumentStatus.READY)
    doc.current_version = 2
    vectors.points[stale_chunk.id] = [1.0, 0.0]

    message = IndexMessage(doc.id, IndexOperation.REINDEX, 1)
    await services.dispatcher.dispatch(message.operation.routing_key, message)

    assert vectors.points == {}
    assert doc.status is DocumentStatus.READY


@pytest.mark.asyncio
async def test_terminal_failure_cleans_target_points_and_records_error() -> None:
    doc, chunk, services, vectors = setup(DocumentStatus.INDEXING)
    vectors.points[chunk.id] = [1.0, 0.0]

    await services.failure_handler.handle(
        IndexMessage(doc.id, IndexOperation.INGEST, 1),
        RuntimeError("ollama down"),
    )

    assert vectors.points == {}
    assert doc.status is DocumentStatus.FAILED
    assert doc.last_error == "RuntimeError: ollama down"


@pytest.mark.asyncio
async def test_qdrant_success_then_postgres_failure_converges_on_retry() -> None:
    doc = Document(uuid4(), "doc.md", SourceType.MARKDOWN, "text", "hash")
    chunk = Chunk(uuid4(), doc.id, 1, 0, "text")
    documents = ActivateFailsOnce(doc)
    vectors = Vectors()
    services = create_worker_services(documents, Chunks([chunk]), Embedder(), vectors)
    message = IndexMessage(doc.id, IndexOperation.INGEST, 1)

    with pytest.raises(RuntimeError, match="postgres switch failed") as failure:
        await services.dispatcher.dispatch(message.operation.routing_key, message)
    assert doc.status is DocumentStatus.INDEXING
    assert vectors.points == {chunk.id: [1.0, 0.0]}

    await services.retry_handler.handle(message, failure.value)
    assert doc.status is DocumentStatus.PENDING
    assert doc.last_error == "RuntimeError: postgres switch failed"

    await services.dispatcher.dispatch(message.operation.routing_key, message)

    assert doc.status is DocumentStatus.READY
    assert doc.last_error is None
    assert vectors.points == {chunk.id: [1.0, 0.0]}


@pytest.mark.asyncio
async def test_terminal_failure_records_exception_type_when_message_is_empty() -> None:
    doc, _, services, _ = setup(DocumentStatus.INDEXING)

    await services.failure_handler.handle(
        IndexMessage(doc.id, IndexOperation.INGEST, 1),
        TimeoutError(),
    )

    assert doc.status is DocumentStatus.FAILED
    assert doc.last_error == "TimeoutError"


@pytest.mark.asyncio
async def test_delete_retry_keeps_document_deleting() -> None:
    doc, _, services, _ = setup(DocumentStatus.DELETING)

    await services.retry_handler.handle(
        IndexMessage(doc.id, IndexOperation.DELETE, 1),
        RuntimeError("qdrant unavailable"),
    )

    assert doc.status is DocumentStatus.DELETING
    assert doc.last_error is None


@pytest.mark.asyncio
async def test_duplicate_delete_is_idempotent() -> None:
    doc, chunk, services, vectors = setup(DocumentStatus.DELETING)
    vectors.points[chunk.id] = [1.0, 0.0]
    message = IndexMessage(doc.id, IndexOperation.DELETE, 1)

    await services.dispatcher.dispatch(message.operation.routing_key, message)
    await services.dispatcher.dispatch(message.operation.routing_key, message)

    assert vectors.points == {}
    assert doc.status is DocumentStatus.DELETED


@pytest.mark.asyncio
async def test_dispatcher_rejects_unknown_routing_key() -> None:
    doc, _, services, _ = setup()
    message = IndexMessage(doc.id, IndexOperation.INGEST, 1)

    with pytest.raises(ValueError, match="unsupported indexing routing key"):
        await services.dispatcher.dispatch("document.unknown", message)


@pytest.mark.asyncio
async def test_dispatcher_maps_each_routing_key_to_its_own_handler() -> None:
    ingest = RecordingHandler()
    reindex = RecordingHandler()
    delete = RecordingHandler()
    dispatcher = IndexingDispatcher(ingest, reindex, delete)
    document_id = uuid4()
    ingest_message = IndexMessage(document_id, IndexOperation.INGEST, 1)
    reindex_message = IndexMessage(document_id, IndexOperation.REINDEX, 1)
    delete_message = IndexMessage(document_id, IndexOperation.DELETE, 1)

    await dispatcher.dispatch("document.ingest", ingest_message)
    await dispatcher.dispatch("document.reindex", reindex_message)
    await dispatcher.dispatch("document.delete", delete_message)

    assert ingest.messages == [ingest_message]
    assert reindex.messages == [reindex_message]
    assert delete.messages == [delete_message]


@pytest.mark.asyncio
async def test_dispatcher_rejects_operation_routing_key_mismatch() -> None:
    doc, _, services, _ = setup()
    message = IndexMessage(doc.id, IndexOperation.REINDEX, 1)

    with pytest.raises(ValueError, match="does not match"):
        await services.dispatcher.dispatch("document.ingest", message)
