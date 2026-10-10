from dataclasses import dataclass
from uuid import UUID

from rag.services.documents.types.document import SourceType


@dataclass(frozen=True, slots=True)
class StoredFile:
    id: UUID
    filename: str
    file_path: str
    source_type: SourceType
    content_hash: str
    size_bytes: int | None

    @property
    def url(self) -> str:
        return f"/v1/files/{self.id}"
