from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from rag.use_cases.common import ConflictError, DependencyError, NotFoundError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={"code": "not_found", "message": str(exc)},
        )

    @app.exception_handler(ConflictError)
    async def conflict(_: Request, exc: ConflictError):
        return JSONResponse(
            status_code=409,
            content={"code": "conflict", "message": str(exc)},
        )

    @app.exception_handler(DependencyError)
    async def unavailable(_: Request, exc: DependencyError):
        return JSONResponse(
            status_code=503,
            content={"code": "dependency_unavailable", "message": str(exc)},
        )

    @app.exception_handler(ValueError)
    async def invalid_input(_: Request, exc: ValueError):
        return JSONResponse(
            status_code=422,
            content={"code": "invalid_input", "message": str(exc)},
        )
