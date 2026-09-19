from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VectorRecord:
    id: UUID
    vector: list[float]
