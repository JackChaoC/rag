from rag.services.files.file_service import FileService


class UploadFileUseCase:
    def __init__(self, fileService: FileService):
        self.fileService = fileService

    async def execute(self, data: bytes, filename: str):
        return await self.fileService.upload(data, filename)
