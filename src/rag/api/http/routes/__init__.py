from fastapi import APIRouter

from rag.api.http.routes import chunks, documents, health, search

api_router = APIRouter(prefix="/v1")
api_router.include_router(documents.router)
api_router.include_router(chunks.router)
api_router.include_router(search.router)

root_router = APIRouter()
root_router.include_router(health.router)
