from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SearchHit:
    chunk_id: UUID
    score: float
