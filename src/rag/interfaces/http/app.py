from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from rag.container import Container, create_container
from rag.interfaces.http.exception_handlers import register_exception_handlers
from rag.interfaces.http.routes import (
    api_router,
    documents,
    health,
    root_router,
    search,
)
from rag.interfaces.mcp.server import create_mcp_server
from rag.resources import container_lifespan


def create_app(container: Container | None = None) -> FastAPI:
    container = container or create_container()
    container.wire(modules=[documents, search, health])
    mcp = create_mcp_server(
        search_knowledge_provider=container.search_knowledge,
        get_document_chunk_provider=container.get_document_chunk,
        list_documents_provider=container.list_documents,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            async with container_lifespan(container), mcp.session_manager.run():
                yield
        finally:
            container.unwire()

    app = FastAPI(title="RAG Service", version="0.1.0", lifespan=lifespan)
    app.state.container = container

    register_exception_handlers(app)
    app.include_router(api_router)
    app.include_router(root_router)

    frontend_dir = Path(__file__).resolve().parents[4] / "frontend"
    if frontend_dir.is_dir():
        app.mount("/ui", StaticFiles(directory=frontend_dir, html=True), name="ui")
    app.mount(
        "/",
        mcp.streamable_http_app(
            streamable_http_path="/mcp",
            stateless_http=True,
            json_response=True,
        ),
    )
    return app
