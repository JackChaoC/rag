from dependency_injector.wiring import inject
from fastapi import APIRouter

from rag.api.http.dependencies import SearchKnowledgeDep
from rag.api.http.schemas import SearchItem, SearchRequest

router = APIRouter(tags=["search"])


@router.post("/search", response_model=list[SearchItem])
@inject
async def search(
    request: SearchRequest,
    use_case: SearchKnowledgeDep,
) -> list[SearchItem]:
    results = await use_case.execute(request.query, request.top_k)
    return [SearchItem.model_validate(item, from_attributes=True) for item in results]
