from uuid import uuid4

import pytest

from rag.services.documents.types.document import DocumentStatus, SourceType
from rag.services.publisher.types.message import IndexMessage, IndexOperation
from rag.worker.dispatcher import IndexingDispatcher


class RecordingHandler:
    def __init__(self):
        self.messages = []

    async def handle(self, message):
        self.messages.append(message)


async def setup(container):
    file = await container.use_cases.uploadFileUseCase().execute(
        b"# Guide\nintro\n## Topic\nbody", "doc.md"
    )
    result = await container.use_cases.ingestDocumentUseCase().execute(file.url, "Guide")
    return IndexMessage(result.document_id, IndexOperation.INGEST, 1)


async def test_duplicate_ingest_converges_and_stale_message_does_not_remove_new_nodes(
    appContainer,
):
    message = await setup(appContainer)
    dispatcher = appContainer.worker.dispatcher()
    await dispatcher.dispatch("document.ingest", message)
    before = await appContainer.services.chunkLookupService().listChunks(
        message.document_id
    )
    await dispatcher.dispatch("document.ingest", message)
    after = await appContainer.services.chunkLookupService().listChunks(
        message.document_id
    )
    assert [n.chunk_id for n in before] == [n.chunk_id for n in after]
    document = await appContainer.services.documentService().get(message.document_id)
    document.current_version = 2
    await dispatcher.dispatch("document.ingest", message)
    assert (
        await appContainer.services.chunkLookupService().listChunks(document.id)
        == after
    )
    assert document.status is DocumentStatus.READY


async def test_qdrant_success_then_database_failure_converges_on_retry(appContainer):
    message = await setup(appContainer)
    service = appContainer.services.documentService()
    original = service.set_status
    fail = True

    async def set_status(documentId, status, **kwargs):
        nonlocal fail
        if status is DocumentStatus.READY and fail:
            fail = False
            raise RuntimeError("db status failed")
        return await original(documentId, status, **kwargs)

    service.set_status = set_status
    with pytest.raises(RuntimeError, match="db status failed"):
        await appContainer.worker.dispatcher().dispatch("document.ingest", message)
    await appContainer.worker.dispatcher().dispatch("document.ingest", message)
    assert (await service.get(message.document_id)).status is DocumentStatus.READY
    assert (
        len(
            await appContainer.services.chunkLookupService().listChunks(
                message.document_id
            )
        )
        == 2
    )


async def test_terminal_failure_cleans_nodes_and_records_error(appContainer):
    message = await setup(appContainer)
    await appContainer.worker.dispatcher().dispatch("document.ingest", message)
    await appContainer.services.documentService().set_status(
        message.document_id, DocumentStatus.INDEXING
    )
    await appContainer.worker.failureHandler().handle(
        message, RuntimeError("ollama down")
    )
    document = await appContainer.services.documentService().get(message.document_id)
    assert document.status is DocumentStatus.FAILED
    assert document.last_error == "RuntimeError: ollama down"
    assert (
        await appContainer.services.chunkLookupService().listChunks(document.id) == []
    )


async def test_duplicate_delete_removes_nodes_and_preserves_uploaded_file(appContainer):
    message = await setup(appContainer)
    await appContainer.worker.dispatcher().dispatch("document.ingest", message)
    document = await appContainer.services.documentService().get(message.document_id)
    path = appContainer.services.fileService().path(document.file_path)
    await appContainer.use_cases.deleteDocumentUseCase().execute(document.id)
    message = IndexMessage(document.id, IndexOperation.DELETE, 1)
    for _ in range(2):
        await appContainer.worker.dispatcher().dispatch("document.delete", message)
    assert document.status is DocumentStatus.DELETED
    assert path.exists()
    assert (
        await appContainer.services.chunkLookupService().listChunks(document.id) == []
    )


async def test_dispatcher_rejects_unknown_and_mismatched_routing_keys():
    handler = RecordingHandler()
    dispatcher = IndexingDispatcher(handler, handler, handler)
    message = IndexMessage(uuid4(), IndexOperation.REINDEX, 1)
    with pytest.raises(ValueError, match="unsupported"):
        await dispatcher.dispatch("document.unknown", message)
    with pytest.raises(ValueError, match="does not match"):
        await dispatcher.dispatch("document.ingest", message)


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


async def test_failed_delete_is_not_resurrected_by_delayed_ingest(appContainer):
    message = await setup(appContainer)
    await appContainer.use_cases.deleteDocumentUseCase().execute(message.document_id)
    await appContainer.worker.failureHandler().handle(
        IndexMessage(message.document_id, IndexOperation.DELETE, 1),
        RuntimeError("delete failed"),
    )
    await appContainer.worker.dispatcher().dispatch("document.ingest", message)
    document = await appContainer.services.documentService().get(message.document_id)
    assert document.status is DocumentStatus.DELETING
    assert document.last_error == "RuntimeError: delete failed"
