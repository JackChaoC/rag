from fastapi import APIRouter

from rag.interfaces.http.routes import documents, health, search


api_router = APIRouter(prefix="/v1")
api_router.include_router(documents.router)
api_router.include_router(search.router)

root_router = APIRouter()
root_router.include_router(health.router)
