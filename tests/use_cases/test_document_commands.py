from dataclasses import replace
from uuid import uuid4

import pytest

from rag.core.document_processing.parser import DocumentParser
from rag.infrastructure.database.entities.document import Document, DocumentStatus, SourceType
from rag.use_cases.common import DependencyError
from rag.use_cases.delete_document import DeleteDocument
from rag.use_cases.ingest_document import IngestDocument
from rag.use_cases.reindex_document import ReindexDocument


class Documents:
    def __init__(self, document: Document | None = None) -> None:
        self.document = document
        self.added_versions = []
        self.status_changes = []

    async def get(self, document_id):
        return self.document if self.document and self.document.id == document_id else None

    async def get_by_source_uri(self, source_uri):
        return self.document if self.document and self.document.source_uri == source_uri else None

    async def create_with_chunks(self, document, chunks):
        self.document = document

    async def add_version(self, document, chunks):
        self.document = document
        self.added_versions.append((document, chunks))

    async def set_status(self, document_id, status, *, error=None, expected=None):
        self.status_changes.append((status, error))
        if self.document:
            self.document.status = status
            self.document.last_error = error
        return True


def document(status=DocumentStatus.READY) -> Document:
    import hashlib

    content = "# Stable\n\nContent\n"
    return Document(
        uuid4(), "stable.md", SourceType.MARKDOWN, content,
        hashlib.sha256(content.encode()).hexdigest(), status=status,
    )


@pytest.mark.asyncio
async def test_reindex_without_content_change_keeps_version() -> None:
    current = document()
    documents = Documents(current)
    published = []

    async def publish(message):
        published.append(message)

    result = await ReindexDocument(None, documents, publish).execute(current.id)

    assert result.version == 1
    assert documents.added_versions == []
    assert published == []


@pytest.mark.asyncio
async def test_pending_unchanged_reindex_republishes_same_version() -> None:
    current = document(DocumentStatus.PENDING)
    documents = Documents(current)
    published = []

    async def publish(message):
        published.append(message)

    result = await ReindexDocument(None, documents, publish).execute(current.id)

    assert result.version == 1
    assert published[0].version == 1
    assert documents.added_versions == []


@pytest.mark.asyncio
async def test_ingest_confirm_failure_becomes_dependency_error() -> None:
    documents = Documents()

    async def fail(_message):
        raise OSError("confirm failed")

    with pytest.raises(DependencyError):
        await IngestDocument(DocumentParser(), documents, fail).execute(
            b"# New", "new.md", SourceType.MARKDOWN,
        )

    assert documents.document.status is DocumentStatus.FAILED
    assert documents.document.last_error == "confirm failed"


@pytest.mark.asyncio
async def test_delete_confirm_failure_keeps_retriable_deleting_state() -> None:
    current = document()
    documents = Documents(current)

    async def fail(_message):
        raise OSError("confirm failed")

    with pytest.raises(DependencyError):
        await DeleteDocument(documents, fail).execute(current.id)

    assert current.status is DocumentStatus.DELETING
    assert current.last_error == "confirm failed"
