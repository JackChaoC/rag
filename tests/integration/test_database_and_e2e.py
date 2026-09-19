import asyncio
import os
from io import BytesIO
from uuid import uuid4

import pytest
from psycopg.errors import ForeignKeyViolation, UniqueViolation
from reportlab.pdfgen import canvas

from rag.config import Settings
from rag.container import Container
from rag.indexing import IndexingWorker
from rag.infrastructure.database.client import Database
from rag.infrastructure.database.entities.chunk import Chunk
from rag.infrastructure.database.entities.document import Document, DocumentStatus, SourceType
from rag.infrastructure.database.repositories.chunk_repository import ChunkRepository
from rag.infrastructure.database.repositories.document_repository import DocumentRepository


pytestmark = pytest.mark.integration


def require_services() -> None:
    if os.getenv("RUN_RAG_INTEGRATION") != "1":
        pytest.skip("set RUN_RAG_INTEGRATION=1 after starting local services")


async def wait_for_status(container: Container, document_id, status: DocumentStatus, timeout=240):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        document = await container.documents.get(document_id)
        if document and document.status is status:
            return document
        if document and document.status is DocumentStatus.FAILED:
            raise AssertionError(f"document failed: {document.last_error}")
        await asyncio.sleep(0.25)
    raise TimeoutError(f"document did not reach {status.value}")


@pytest.mark.asyncio
async def test_database_constraints_and_active_hydration() -> None:
    require_services()
    database = Database(Settings().database_url)
    await database.connect()
    pool = database.require_pool()
    documents = DocumentRepository(pool)
    document_id, chunk_id = uuid4(), uuid4()
    document = Document(
        document_id, f"constraint-{document_id}.md", SourceType.MARKDOWN,
        "# Constraint", "hash", status=DocumentStatus.PENDING,
    )
    chunk = Chunk(chunk_id, document_id, 1, 0, "# Constraint")
    try:
        await documents.create_with_chunks(document, [chunk])
        async with pool.connection() as connection:
            with pytest.raises(ForeignKeyViolation):
                async with connection.transaction():
                    await connection.execute('DELETE FROM "documents" WHERE id=%s', (document_id,))
            with pytest.raises(UniqueViolation):
                async with connection.transaction():
                    await connection.execute(
                        '''INSERT INTO "chunks"
                           (id, document_id, version, chunk_index, content, metadata, active)
                           VALUES (%s,%s,1,0,'duplicate','{}',FALSE)''',
                        (uuid4(), document_id),
                    )

        chunks = ChunkRepository(pool)
        assert await chunks.hydrate([chunk_id]) == {}
        await documents.activate_version(document_id, 1)
        assert chunk_id in await chunks.hydrate([chunk_id])
    finally:
        async with pool.connection() as connection, connection.transaction():
            await connection.execute('DELETE FROM "chunks" WHERE document_id=%s', (document_id,))
            await connection.execute('DELETE FROM "documents" WHERE id=%s', (document_id,))
        await database.close()


@pytest.mark.asyncio
async def test_pdf_to_postgres_rabbit_ollama_qdrant_search_rebuild_and_delete() -> None:
    require_services()
    settings = Settings()
    container = Container(settings)
    await container.start()
    worker = IndexingWorker(container.documents, container.chunks, container.embedder, container.vectors)
    await container.broker.consume(worker.handle, worker.fail)
    source_uri = f"e2e-{uuid4()}.pdf"
    document_id = None
    output = BytesIO()
    page = canvas.Canvas(output)
    page.setTitle("RAG E2E")
    page.drawString(72, 740, "RAG Architecture")
    page.drawString(72, 710, "PostgreSQL stores document and chunk facts.")
    page.drawString(72, 680, "Qdrant stores chunk embedding vectors.")
    page.save()

    try:
        created = await container.ingest.execute(
            output.getvalue(), source_uri, SourceType.PDF, "RAG E2E", {"kind": "test"},
        )
        document_id = created.document_id
        ready = await wait_for_status(container, document_id, DocumentStatus.READY)
        chunks = await container.chunks.for_version(document_id, ready.current_version)
        assert chunks
        assert "PostgreSQL stores document" in ready.content

        info = await container.qdrant.get_collection(settings.qdrant_collection)
        dimension = info.config.params.vectors.size
        assert dimension > 0
        points = await container.qdrant.retrieve(
            settings.qdrant_collection, ids=[str(chunks[0].id)],
            with_payload=True, with_vectors=False,
        )
        assert len(points) == 1
        assert not points[0].payload
        print(f"embedding_model={settings.embedding_model} dimension={dimension} distance=Cosine")

        results = await container.search.execute("Where are embedding vectors stored?", 1)
        assert results and results[0].document_id == document_id
        assert results[0].source_uri == source_uri

        unchanged = await container.reindex.execute(document_id)
        assert unchanged.version == ready.current_version

        await container.vectors.recreate(dimension)
        assert await worker.rebuild_all() == len(chunks)
        rebuilt = await container.qdrant.retrieve(
            settings.qdrant_collection, ids=[str(chunk.id) for chunk in chunks],
            with_payload=True, with_vectors=False,
        )
        assert {str(point.id) for point in rebuilt} == {str(chunk.id) for chunk in chunks}

        await container.delete.execute(document_id)
        await wait_for_status(container, document_id, DocumentStatus.DELETED)
        deleted = await container.qdrant.retrieve(
            settings.qdrant_collection, ids=[str(chunk.id) for chunk in chunks],
            with_vectors=False,
        )
        assert deleted == []
    finally:
        if document_id is not None:
            pool = container.database.require_pool()
            async with pool.connection() as connection, connection.transaction():
                await connection.execute('DELETE FROM "chunks" WHERE document_id=%s', (document_id,))
                await connection.execute('DELETE FROM "documents" WHERE id=%s', (document_id,))
        await container.close()
