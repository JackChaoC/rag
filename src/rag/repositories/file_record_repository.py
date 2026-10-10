from rag.resources.postgresql.models import FileRecord
from rag.services.files.types.stored_file import StoredFile


class FileRecordRepository:
    def __init__(self, sessions):
        self.sessions = sessions

    async def create(self, file):
        async with self.sessions.begin() as session:
            session.add(FileRecord(id=file.id, filename=file.filename, file_path=file.file_path,
                                   source_type=file.source_type, content_hash=file.content_hash,
                                   size_bytes=file.size_bytes))

    async def get(self, fileId):
        async with self.sessions() as session:
            row = await session.get(FileRecord, fileId)
            if row is None:
                return None
            return StoredFile(row.id, row.filename, row.file_path, row.source_type,
                              row.content_hash, row.size_bytes)
