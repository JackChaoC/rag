import json
from pathlib import Path
from uuid import UUID

from dependency_injector.wiring import inject
from fastapi import APIRouter, File, Form, UploadFile

from rag.infrastructure.database.entities.document import SourceType
from rag.interfaces.http.dependencies import (
    DeleteDocumentDep,
    GetDocumentChunkDep,
    IngestDocumentDep,
    ListDocumentsDep,
    ReindexDocumentDep,
)
from rag.interfaces.http.schemas import ChunkResponse, DocumentResponse, ErrorResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    status_code=202,
    response_model=DocumentResponse,
    responses={
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
@inject
async def ingest_document(
    use_case: IngestDocumentDep,
    file: UploadFile = File(...),
    source_uri: str = Form(...),
    title: str | None = Form(None),
    metadata: str = Form("{}"),
) -> DocumentResponse:
    result = await use_case.execute(
        await file.read(),
        source_uri,
        _source_type(file.filename),
        title,
        _metadata(metadata),
    )
    return _document_response(result)


@router.post("/{document_id}/reindex", status_code=202, response_model=DocumentResponse)
@inject
async def reindex_document(
    document_id: UUID,
    use_case: ReindexDocumentDep,
    file: UploadFile | None = File(None),
) -> DocumentResponse:
    result = await use_case.execute(document_id, await file.read() if file else None)
    return _document_response(result)


@router.delete("/{document_id}", status_code=202, response_model=DocumentResponse)
@inject
async def delete_document(
    document_id: UUID,
    use_case: DeleteDocumentDep,
) -> DocumentResponse:
    return _document_response(await use_case.execute(document_id))


@router.get("", response_model=list[DocumentResponse])
@inject
async def list_documents(use_case: ListDocumentsDep) -> list[DocumentResponse]:
    return [_document_response(item) for item in await use_case.execute()]


@router.get("/{document_id}/chunks/{chunk_id}", response_model=ChunkResponse)
@inject
async def get_chunk(
    document_id: UUID,
    chunk_id: UUID,
    use_case: GetDocumentChunkDep,
) -> ChunkResponse:
    result = await use_case.execute(document_id, chunk_id)
    return ChunkResponse.model_validate(result, from_attributes=True)


def _metadata(value: str) -> dict:
    try:
        result = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("metadata must be valid JSON") from exc
    if not isinstance(result, dict):
        raise ValueError("metadata must be a JSON object")
    return result


def _source_type(filename: str | None) -> SourceType:
    suffix = Path(filename or "").suffix.lower()
    mapping = {
        ".md": SourceType.MARKDOWN,
        ".markdown": SourceType.MARKDOWN,
        ".txt": SourceType.TEXT,
        ".pdf": SourceType.PDF,
    }
    if suffix not in mapping:
        raise ValueError(f"unsupported file extension: {suffix or '<none>'}")
    return mapping[suffix]


def _document_response(value) -> DocumentResponse:
    return DocumentResponse(
        document_id=value.document_id,
        source_uri=value.source_uri,
        title=value.title,
        version=value.version,
        status=value.status.value,
        metadata=value.metadata,
    )
