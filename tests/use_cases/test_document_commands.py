import pytest

from rag.services.common.errors import ConflictError, DependencyError
from rag.services.documents.types.document import DocumentStatus, SourceType
from rag.services.publisher.types.message import IndexMessage, IndexOperation


async def upload(container, data=b"# Hello\n## World\nbody", uri="doc.md"):
    file = await container.use_cases.uploadFileUseCase().execute(data, uri)
    return await container.use_cases.ingestDocumentUseCase().execute(file.url, "Doc")


async def test_upload_only_stores_file_and_queues_job(appContainer):
    result = await upload(appContainer, b"not a valid PDF", "opaque.md")
    doc = await appContainer.services.documentService().get(result.document_id)
    assert doc.status is DocumentStatus.PENDING
    assert (
        await appContainer.services.fileService().read(doc.file_path)
        == b"not a valid PDF"
    )
    assert await appContainer.services.chunkLookupService().listChunks(doc.id) == []
    appContainer.resources.rabbitmqResource().publish.assert_awaited_once()


async def test_duplicate_ingest_reuses_document_and_different_information_conflicts(appContainer):
    file = await appContainer.use_cases.uploadFileUseCase().execute(b"# Doc", "doc.md")
    ingest = appContainer.use_cases.ingestDocumentUseCase()
    first = await ingest.execute(file.url, "Doc")
    second = await ingest.execute(file.url, "Doc")
    assert first.document_id == second.document_id
    with pytest.raises(ConflictError):
        await ingest.execute(file.url, "Different title")


async def test_upload_confirm_failure_retains_file_and_can_retry(appContainer):
    broker = appContainer.resources.rabbitmqResource()
    broker.publish.side_effect = OSError("confirm failed")
    with pytest.raises(DependencyError):
        await upload(appContainer)
    doc = (await appContainer.services.documentService().list())[0]
    assert doc.status is DocumentStatus.FAILED
    assert await appContainer.services.fileService().read(doc.file_path)
    broker.publish.side_effect = None
    result = await appContainer.use_cases.ingestDocumentUseCase().execute(f"/v1/files/{doc.file_id}", "Doc")
    assert result.document_id == doc.id
    assert broker.publish.await_count == 2


async def test_reindex_replaces_file_and_removes_old_nodes(appContainer):
    created = await upload(appContainer)
    message = IndexMessage(created.document_id, IndexOperation.INGEST, 1)
    await appContainer.worker.dispatcher().dispatch("document.ingest", message)
    doc = await appContainer.services.documentService().get(created.document_id)
    oldPath = appContainer.services.fileService().path(doc.file_path)
    file = await appContainer.use_cases.uploadFileUseCase().execute(b"# Updated", "updated.md")
    result = await appContainer.use_cases.reindexDocumentUseCase().execute(doc.id, file.url)
    assert result.version == 2
    assert oldPath.exists()
    assert await appContainer.services.chunkLookupService().listChunks(doc.id) == []
    await appContainer.worker.dispatcher().dispatch(
        "document.reindex", IndexMessage(doc.id, IndexOperation.REINDEX, 2)
    )
    assert (await appContainer.services.chunkLookupService().listChunks(doc.id))[
        0
    ].content == "# Updated"


async def test_delete_confirm_failure_stays_deleting(appContainer):
    result = await upload(appContainer)
    appContainer.resources.rabbitmqResource().publish.side_effect = OSError(
        "confirm failed"
    )
    with pytest.raises(DependencyError):
        await appContainer.use_cases.deleteDocumentUseCase().execute(result.document_id)
    assert (
        await appContainer.services.documentService().get(result.document_id)
    ).status is DocumentStatus.DELETING


async def test_file_repository_rejects_traversal(appContainer):
    with pytest.raises(ValueError):
        await appContainer.services.fileService().read("../secret")


async def test_concurrent_duplicate_upload_does_not_create_second_document(
    appContainer,
):
    import asyncio

    file = await appContainer.use_cases.uploadFileUseCase().execute(b"# Doc", "doc.md")
    ingest = appContainer.use_cases.ingestDocumentUseCase()
    first, second = await asyncio.gather(ingest.execute(file.url, "Doc"), ingest.execute(file.url, "Doc"))
    assert first.document_id == second.document_id
    assert len(await appContainer.services.documentService().list()) == 1


async def test_bad_pdf_is_accepted_as_file_but_fails_in_worker(appContainer):
    file = await appContainer.use_cases.uploadFileUseCase().execute(b"broken pdf", "bad.pdf")
    result = await appContainer.use_cases.ingestDocumentUseCase().execute(file.url, "Bad PDF")
    message = IndexMessage(result.document_id, IndexOperation.INGEST, 1)
    with pytest.raises(Exception):
        await appContainer.worker.dispatcher().dispatch("document.ingest", message)
    document = await appContainer.services.documentService().get(result.document_id)
    assert document.status is DocumentStatus.PENDING
    await appContainer.worker.failureHandler().handle(message, RuntimeError("invalid PDF"))
    assert document.status is DocumentStatus.FAILED
    assert document.last_error
    assert (
        await appContainer.services.chunkLookupService().listChunks(document.id) == []
    )


async def test_legacy_file_and_document_same_id_does_not_deadlock(appContainer):
    import asyncio
    from rag.services.documents.types.document import Document

    file = await appContainer.use_cases.uploadFileUseCase().execute(b"# Legacy", "legacy.md")
    document = Document(id=file.id, file_id=file.id, title="Legacy",
                        source_type=file.source_type, file_path=file.file_path,
                        content_hash=file.content_hash, status=DocumentStatus.READY)
    await appContainer.services.documentService().create(document)
    result = await asyncio.wait_for(
        appContainer.use_cases.ingestDocumentUseCase().execute(file.url, "Legacy"), timeout=1)
    assert result.document_id == document.id
    appContainer.resources.rabbitmqResource().publish.assert_not_awaited()
