import asyncio
import os
from pathlib import Path
from uuid import UUID, uuid4


class FileRepository:
    def __init__(self, root: str):
        self.root = Path(root).resolve()

    def resolve(self, filePath: str) -> Path:
        path = (self.root / filePath).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("file path escapes storage root")
        return path

    async def store(
        self, documentId: UUID, version: int, extension: str, data: bytes
    ) -> str:
        if extension not in {"md", "txt", "pdf"}:
            raise ValueError("unsupported file format")
        filePath = f"{documentId}/{version}.{extension}"
        path = self.resolve(filePath)

        def write():
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{uuid4()}.tmp")
            try:
                temporary.write_bytes(data)
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)

        await asyncio.to_thread(write)
        return filePath

    async def read(self, filePath: str) -> bytes:
        return await asyncio.to_thread(self.resolve(filePath).read_bytes)

    async def delete(self, filePath: str) -> None:
        await asyncio.to_thread(self.resolve(filePath).unlink, missing_ok=True)
