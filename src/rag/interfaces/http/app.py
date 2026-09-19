from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from rag.config import get_settings
from rag.container import Container
from rag.infrastructure.database.entities.document import SourceType
from rag.interfaces.http.schemas import (
    ChunkResponse, DocumentResponse, ErrorResponse, SearchItem, SearchRequest,
)
from rag.interfaces.mcp.server import create_mcp_server
from rag.use_cases.common import ConflictError, DependencyError, NotFoundError


def create_app(container: Container | None = None) -> FastAPI:
    container = container or Container(get_settings())
    mcp = create_mcp_server(container)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await container.start()
        async with mcp.session_manager.run():
            yield
        await container.close()

    app = FastAPI(title="RAG Service", version="0.1.0", lifespan=lifespan)
    app.state.container = container

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"code": "not_found", "message": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict(_: Request, exc: ConflictError):
        return JSONResponse(status_code=409, content={"code": "conflict", "message": str(exc)})

    @app.exception_handler(DependencyError)
    async def unavailable(_: Request, exc: DependencyError):
        return JSONResponse(status_code=503, content={"code": "dependency_unavailable", "message": str(exc)})

    @app.exception_handler(ValueError)
    async def invalid_input(_: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"code": "invalid_input", "message": str(exc)})

    @app.post("/v1/documents", status_code=202, response_model=DocumentResponse,
              responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
    async def ingest_document(
        file: UploadFile = File(...), source_uri: str = Form(...),
        title: str | None = Form(None), metadata: str = Form("{}"),
    ):
        parsed_metadata = _metadata(metadata)
        result = await container.ingest.execute(
            await file.read(), source_uri, _source_type(file.filename), title, parsed_metadata,
        )
        return _document_response(result)

    @app.post("/v1/documents/{document_id}/reindex", status_code=202, response_model=DocumentResponse)
    async def reindex_document(document_id: UUID, file: UploadFile | None = File(None)):
        result = await container.reindex.execute(document_id, await file.read() if file else None)
        return _document_response(result)

    @app.delete("/v1/documents/{document_id}", status_code=202, response_model=DocumentResponse)
    async def delete_document(document_id: UUID):
        return _document_response(await container.delete.execute(document_id))

    @app.get("/v1/documents", response_model=list[DocumentResponse])
    async def list_documents():
        return [_document_response(item) for item in await container.list_documents.execute()]

    @app.get("/v1/documents/{document_id}/chunks/{chunk_id}", response_model=ChunkResponse)
    async def get_chunk(document_id: UUID, chunk_id: UUID):
        return asdict(await container.get_chunk.execute(document_id, chunk_id))

    @app.post("/v1/search", response_model=list[SearchItem])
    async def search(request: SearchRequest):
        return [asdict(item) for item in await container.search.execute(request.query, request.top_k)]

    @app.get("/health")
    async def health():
        checks: dict[str, bool] = {}
        try:
            checks["postgresql"] = await container.database.ping()
        except Exception:
            checks["postgresql"] = False
        checks["rabbitmq"] = await container.broker.ping()
        try:
            await container.qdrant.get_collections()
            checks["qdrant"] = True
        except Exception:
            checks["qdrant"] = False
        try:
            async with httpx.AsyncClient(base_url=container.settings.ollama_url, timeout=2) as client:
                checks["ollama"] = (await client.get("/api/tags")).is_success
        except Exception:
            checks["ollama"] = False
        ready = all(checks.values())
        return JSONResponse(status_code=200 if ready else 503, content={"ready": ready, "dependencies": checks})

    frontend_dir = Path(__file__).resolve().parents[4] / "frontend"
    if frontend_dir.is_dir():
        app.mount("/ui", StaticFiles(directory=frontend_dir, html=True), name="ui")
    app.mount("/", mcp.streamable_http_app(streamable_http_path="/mcp", stateless_http=True, json_response=True))
    return app


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
    mapping = {".md": SourceType.MARKDOWN, ".markdown": SourceType.MARKDOWN,
               ".txt": SourceType.TEXT, ".pdf": SourceType.PDF}
    if suffix not in mapping:
        raise ValueError(f"unsupported file extension: {suffix or '<none>'}")
    return mapping[suffix]


def _document_response(value) -> DocumentResponse:
    return DocumentResponse(
        document_id=value.document_id, source_uri=value.source_uri, title=value.title,
        version=value.version, status=value.status.value, metadata=value.metadata,
    )
