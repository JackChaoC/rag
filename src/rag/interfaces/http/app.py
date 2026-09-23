from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from rag.config import get_settings
from rag.container import Container
from rag.interfaces.http.exception_handlers import register_exception_handlers
from rag.interfaces.http.routes import api_router, root_router
from rag.interfaces.mcp.dependencies import McpDependencies
from rag.interfaces.mcp.server import create_mcp_server


def create_app(container: Container | None = None) -> FastAPI:
    container = container or Container(get_settings())
    mcp = create_mcp_server(
        McpDependencies(
            provide_search_knowledge=lambda: container.search,
            provide_get_document_chunk=lambda: container.get_chunk,
            provide_list_documents=lambda: container.list_documents,
        )
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await container.start()
        async with mcp.session_manager.run():
            yield
        await container.close()

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
