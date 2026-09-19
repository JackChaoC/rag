from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from uuid import UUID


class IndexOperation(StrEnum):
    INGEST = "ingest"
    REINDEX = "reindex"
    DELETE = "delete"

    @property
    def routing_key(self) -> str:
        return f"document.{self.value}"


@dataclass(frozen=True, slots=True)
class IndexMessage:
    document_id: UUID
    operation: IndexOperation
    version: int

    def encode(self) -> bytes:
        data = asdict(self)
        data["document_id"] = str(self.document_id)
        data["operation"] = self.operation.value
        return json.dumps(data).encode()

    @classmethod
    def decode(cls, body: bytes) -> "IndexMessage":
        data = json.loads(body)
        return cls(UUID(data["document_id"]), IndexOperation(data["operation"]), int(data["version"]))
