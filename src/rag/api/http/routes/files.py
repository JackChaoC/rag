from uuid import UUID

from dependency_injector.wiring import inject
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse

from rag.api.http.dependencies import GetFileDep, UploadFileDep
from rag.api.http.schemas import FileResponse as FileUploadResponse

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", status_code=201, response_model=FileUploadResponse)
@inject
async def upload_file(use_case: UploadFileDep, file: UploadFile = File(...)):
    result = await use_case.execute(await file.read(), file.filename or "")
    return FileUploadResponse(file_id=result.id, url=result.url, filename=result.filename, size_bytes=result.size_bytes)


@router.get("/{file_id}")
@inject
async def get_file(file_id: UUID, use_case: GetFileDep, download: bool = False):
    file, path = await use_case.execute(file_id)
    media_type = "application/pdf" if file.source_type.value == "pdf" else "text/plain"
    return FileResponse(path, media_type=media_type, filename=file.filename,
                        content_disposition_type="attachment" if download else "inline",
                        headers={"X-Content-Type-Options": "nosniff"})
