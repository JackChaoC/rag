import hashlib
from pathlib import Path
from uuid import UUID, uuid4

from rag.repositories.file_repository import FileRepository
from rag.repositories.file_record_repository import FileRecordRepository
from rag.services.common.errors import NotFoundError
from rag.services.documents.types.document import SourceType
from rag.services.files.types.stored_file import StoredFile


class FileService:
    def __init__(self, fileRepository: FileRepository, fileRecordRepository: FileRecordRepository):
        self.fileRepository = fileRepository
        self.fileRecordRepository = fileRecordRepository

    async def upload(self, data: bytes, filename: str) -> StoredFile:
        filename = Path(filename.replace("\\", "/")).name
        types = {".md": SourceType.MARKDOWN, ".markdown": SourceType.MARKDOWN,
                 ".txt": SourceType.TEXT, ".pdf": SourceType.PDF}
        sourceType = types.get(Path(filename).suffix.lower())
        if sourceType is None:
            raise ValueError("unsupported file extension")
        if not data:
            raise ValueError("file is empty")
        fileId = uuid4()
        extension = {SourceType.MARKDOWN: "md", SourceType.TEXT: "txt", SourceType.PDF: "pdf"}[sourceType]
        path = await self.fileRepository.store(fileId, 1, extension, data)
        file = StoredFile(fileId, filename, path, sourceType, hashlib.sha256(data).hexdigest(), len(data))
        try:
            await self.fileRecordRepository.create(file)
        except Exception:
            await self.fileRepository.delete(path)
            raise
        return file

    async def get(self, fileId: UUID) -> StoredFile:
        file = await self.fileRecordRepository.get(fileId)
        if file is None:
            raise NotFoundError("file not found")
        return file

    async def fromUrl(self, url: str) -> StoredFile:
        # Only URLs returned by this service; never fetch arbitrary remote URLs.
        prefix = "/v1/files/"
        if not url.startswith(prefix):
            raise ValueError("file_url must be a URL returned by the upload endpoint")
        try:
            fileId = UUID(url[len(prefix):])
        except ValueError as exc:
            raise ValueError("invalid file_url") from exc
        if url != f"{prefix}{fileId}":
            raise ValueError("invalid file_url")
        return await self.get(fileId)

    async def read(self, filePath: str) -> bytes:
        return await self.fileRepository.read(filePath)

    async def delete(self, filePath: str) -> None:
        await self.fileRepository.delete(filePath)

    def path(self, filePath: str):
        return self.fileRepository.resolve(filePath)
