from uuid import UUID

from rag.repositories.file_repository import FileRepository


class FileService:
    def __init__(self, fileRepository: FileRepository):
        self.fileRepository = fileRepository

    async def store(
        self, documentId: UUID, version: int, sourceType, data: bytes
    ) -> str:
        extensions = {"markdown": "md", "text": "txt", "pdf": "pdf"}
        return await self.fileRepository.store(
            documentId, version, extensions[sourceType.value], data
        )

    async def read(self, filePath: str) -> bytes:
        return await self.fileRepository.read(filePath)

    async def delete(self, filePath: str) -> None:
        await self.fileRepository.delete(filePath)

    def path(self, filePath: str):
        return self.fileRepository.resolve(filePath)
