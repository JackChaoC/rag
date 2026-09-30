from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    content: str
    chunk_index: int
    start_line: int
    end_line: int
    token_count: int
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class Section:
    lines: list[tuple[int, str]]
    heading: str | None


@dataclass(frozen=True, slots=True)
class Piece:
    text: str
    start_line: int
    end_line: int
    separator: str = "\n"
