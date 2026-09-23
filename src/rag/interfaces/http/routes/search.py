from fastapi import APIRouter

from rag.interfaces.http.dependencies import SearchKnowledgeDep
from rag.interfaces.http.schemas import SearchItem, SearchRequest


router = APIRouter(tags=["search"])


@router.post("/search", response_model=list[SearchItem])
async def search(
    request: SearchRequest,
    use_case: SearchKnowledgeDep,
) -> list[SearchItem]:
    results = await use_case.execute(request.query, request.top_k)
    return [SearchItem.model_validate(item, from_attributes=True) for item in results]
