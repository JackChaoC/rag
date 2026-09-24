from dependency_injector.wiring import inject
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from rag.interfaces.http.dependencies import CheckHealthDep
from rag.interfaces.http.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
@inject
async def health(use_case: CheckHealthDep) -> JSONResponse:
    result = await use_case.execute()
    return JSONResponse(
        status_code=200 if result.ready else 503,
        content={"ready": result.ready, "dependencies": result.dependencies},
    )
