import asyncio
import os
from io import BytesIO
from uuid import uuid4

import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import delete, inspect
from sqlalchemy.exc import IntegrityError

from rag.config import Settings
from rag.containers import create_container
from rag.containers.resources import container_lifespan, resolve
from rag.repositories.document_repository import DocumentRepository
from rag.resources.postgresql.client import PostgreSQLResource
from rag.resources.postgresql.models import DocumentRecord, FileRecord
from rag.services.documents.types.document import Document, DocumentStatus, SourceType

pytestmark = pytest.mark.integration


def require_services():
    if os.getenv("RUN_RAG_INTEGRATION") != "1":
        pytest.skip("set RUN_RAG_INTEGRATION=1 with a migrated NEW database")


async def test_database_constraints_and_document_lock():
    require_services()
    database = PostgreSQLResource(Settings().database_url)
    await database.connect()
    sessions = database.require_session_factory()
    repository = DocumentRepository(sessions, database.lockEngine)
    fileId = uuid4()
    async with sessions.begin() as session:
        session.add(FileRecord(id=fileId, filename="test.md", file_path=f"{fileId}/test.md", source_type=SourceType.MARKDOWN, content_hash="hash", size_bytes=1))
    doc = Document(uuid4(), fileId, "Test", SourceType.MARKDOWN, "test.md", "hash")
    entered = asyncio.Event()
    try:
        async with database.engine.connect() as connection:
            tables = await connection.run_sync(
                lambda sync: inspect(sync).get_table_names()
            )
            assert "documents" in tables and "chunks" not in tables
        await repository.create(doc)
        with pytest.raises(IntegrityError):
            await repository.create(
                Document(uuid4(), uuid4(), "Invalid file reference", SourceType.TEXT, "test.txt", "hash")
            )
        assert (await repository.get(doc.id)).file_path == "test.md"

        async def contender():
            async with repository.lock(doc.id):
                entered.set()

        async with repository.lock(doc.id):
            task = asyncio.create_task(contender())
            await asyncio.sleep(0.1)
            assert not entered.is_set()
        await asyncio.wait_for(task, 5)
        assert entered.is_set()
    finally:
        async with sessions.begin() as session:
            await session.execute(
                delete(DocumentRecord).where(DocumentRecord.id == doc.id)
            )
        async with sessions.begin() as session:
            await session.execute(delete(FileRecord).where(FileRecord.id == fileId))
        await database.close()


async def test_pdf_upload_worker_search_update_rebuild_delete(tmp_path):
    require_services()
    token = uuid4().hex
    settings = Settings(
        storage_path=str(tmp_path),
        qdrant_collection=f"rag_llama_index_test_{token}",
        rabbitmq_namespace=f"rag.llama-index.test.{token}",
        rabbitmq_retry_delays=(1, 1, 1),
    )
    container = create_container(settings)
    documentId = None
    uploaded = None
    async with container_lifespan(container):
        broker = await resolve(container.resources.rabbitmqResource)
        dispatcher = await resolve(container.worker.dispatcher)
        failureHandler = await resolve(container.worker.failureHandler)
        await broker.consume(dispatcher.dispatch, failureHandler.handle)
        documentService = await resolve(container.services.documentService)
        lookup = await resolve(container.services.chunkLookupService)

        async def wait_status(status):
            async with asyncio.timeout(240):
                while True:
                    doc = await documentService.get(documentId)
                    if doc.status is status:
                        return doc
                    if doc.status is DocumentStatus.FAILED:
                        raise AssertionError(doc.last_error)
                    await asyncio.sleep(0.2)

        output = BytesIO()
        page = canvas.Canvas(output)
        page.drawString(
            72, 740, "Qdrant stores full chunk Nodes and embedding vectors."
        )
        page.save()
        try:
            upload = await resolve(container.use_cases.uploadFileUseCase)
            uploaded = await upload.execute(output.getvalue(), f"{token}.pdf")
            ingest = await resolve(container.use_cases.ingestDocumentUseCase)
            result = await ingest.execute(uploaded.url, "Qdrant")
            documentId = result.document_id
            await wait_status(DocumentStatus.READY)
            chunks = await lookup.listChunks(documentId)
            assert chunks and "Qdrant" in chunks[0].content
            qdrant = await resolve(container.resources.qdrantResource)
            info = await qdrant.get_collection(settings.qdrant_collection)
            vectorConfigs = info.config.params.vectors
            config = (
                next(iter(vectorConfigs.values()))
                if isinstance(vectorConfigs, dict)
                else vectorConfigs
            )
            print(
                f"model={settings.embedding_model} dimension={config.size} distance={config.distance}"
            )
            detail = await lookup.getChunkDetail(chunks[0].chunk_id)
            assert detail.metadata["chunk_index"] == 0
            query = await resolve(container.use_cases.queryKnowledgeUseCase)
            hits = await query.execute("Where are chunks stored?", 1)
            assert hits and hits[0].document_id == documentId
            duplicate = await ingest.execute(uploaded.url, "Qdrant")
            assert duplicate.version == 1
            reindex = await resolve(container.use_cases.reindexDocumentUseCase)
            assert (await reindex.execute(documentId)).version == 2
            await wait_status(DocumentStatus.READY)
            assert (await lookup.listChunks(documentId))[0].chunk_id != chunks[
                0
            ].chunk_id
            await qdrant.delete_collection(settings.qdrant_collection)
            rebuild = await resolve(container.use_cases.rebuildIndexUseCase)
            # This database must be dedicated to integration tests: rebuild queues stored docs.
            assert await rebuild.execute() >= 1
            await wait_status(DocumentStatus.READY)
            deleteUseCase = await resolve(container.use_cases.deleteDocumentUseCase)
            await deleteUseCase.execute(documentId)
            doc = await wait_status(DocumentStatus.DELETED)
            assert await lookup.listChunks(documentId) == []
            assert (tmp_path / doc.file_path).exists()
        finally:
            # Only this test's unique collection, queues and row are removed.
            await broker.close()
            qdrant = await resolve(container.resources.qdrantResource)
            if await qdrant.collection_exists(settings.qdrant_collection):
                await qdrant.delete_collection(settings.qdrant_collection)
            database = await resolve(container.resources.postgresqlResource)
            if documentId:
                async with database.require_session_factory().begin() as session:
                    await session.execute(
                        delete(DocumentRecord).where(DocumentRecord.id == documentId)
                    )
            if uploaded:
                async with database.require_session_factory().begin() as session:
                    await session.execute(delete(FileRecord).where(FileRecord.id == uploaded.id))
    # Reconnect solely to delete this run's explicitly named RabbitMQ topology.
    from rag.resources.rabbitmq.broker import RabbitMQResource

    cleanupBroker = RabbitMQResource(
        settings.rabbitmq_url, (1, 1, 1), namespace=settings.rabbitmq_namespace
    )
    try:
        await cleanupBroker.connect()
        for suffix in ("jobs", "worker-heartbeat", "dead", "retry.1", "retry.2", "retry.3"):
            await cleanupBroker.channel.queue_delete(
                f"{settings.rabbitmq_namespace}.{suffix}"
            )
        for suffix in ("", ".retry", ".dlx"):
            await cleanupBroker.channel.exchange_delete(
                settings.rabbitmq_namespace + suffix
            )
    finally:
        await cleanupBroker.close()
