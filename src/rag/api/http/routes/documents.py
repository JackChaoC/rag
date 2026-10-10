from uuid import UUID

from dependency_injector.wiring import inject
from fastapi import APIRouter, Body

from rag.api.http.dependencies import (
    DeleteDocumentDep,
    GetDocumentChunkDep,
    IngestDocumentDep,
    ListDocumentChunksDep,
    ListDocumentsDep,
    ReindexDocumentDep,
)
from rag.api.http.schemas import ChunkResponse, DocumentResponse, ErrorResponse, DocumentRequest, ReindexRequest
from rag.services.common.errors import NotFoundError

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
    body: DocumentRequest,
) -> DocumentResponse:
    result = await use_case.execute(**body.model_dump())
    return _document_response(result)


@router.post("/{document_id}/reindex", status_code=202, response_model=DocumentResponse)
@inject
async def reindex_document(
    document_id: UUID,
    use_case: ReindexDocumentDep,
    body: ReindexRequest | None = Body(None),
) -> DocumentResponse:
    result = await use_case.execute(document_id, body.file_url if body else None)
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
    result = await use_case.execute(chunk_id)
    if result.document_id != document_id:
        raise NotFoundError("chunk not found in document")
    return ChunkResponse.model_validate(result, from_attributes=True)


@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
@inject
async def list_chunks(document_id: UUID, use_case: ListDocumentChunksDep):
    return [
        ChunkResponse.model_validate(item, from_attributes=True)
        for item in await use_case.execute(document_id)
    ]



def _document_response(value) -> DocumentResponse:
    return DocumentResponse.model_validate(value, from_attributes=True)
