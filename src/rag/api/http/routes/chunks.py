from uuid import UUID

from dependency_injector.wiring import inject
from fastapi import APIRouter

from rag.api.http.dependencies import GetDocumentChunkDep
from rag.api.http.schemas import ChunkResponse

router = APIRouter(prefix="/chunks", tags=["chunks"])


@router.get("/{chunk_id}", response_model=ChunkResponse)
@inject
async def get_chunk_detail(chunk_id: UUID, use_case: GetDocumentChunkDep):
    return ChunkResponse.model_validate(
        await use_case.execute(chunk_id), from_attributes=True
    )
