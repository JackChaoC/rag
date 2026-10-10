from rag.services.common.errors import NotFoundError
from rag.services.files.file_service import FileService


class GetFileUseCase:
    def __init__(self, fileService: FileService):
        self.fileService = fileService

    async def execute(self, fileId):
        file = await self.fileService.get(fileId)
        path = self.fileService.path(file.file_path)
        if not path.is_file():
            raise NotFoundError("stored file is missing")
        return file, path
