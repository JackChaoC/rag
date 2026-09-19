from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    content: str
    chunk_index: int
    start_line: int
    end_line: int
    token_count: int
    metadata: dict[str, str]


def chunk_markdown(content: str, max_chars: int = 1200) -> list[ChunkDraft]:
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")
    lines = content.splitlines()
    if not lines:
        return []

    sections: list[tuple[int, int, list[str], str | None]] = []
    start = 1
    current: list[str] = []
    heading: str | None = None

    def flush(end: int) -> None:
        nonlocal current, start
        if any(line.strip() for line in current):
            sections.append((start, end, current, heading))
        current = []

    for line_no, line in enumerate(lines, start=1):
        if line.startswith("#") and current:
            flush(line_no - 1)
            start = line_no
        if line.startswith("#"):
            heading = line.lstrip("#").strip() or None
        current.append(line)
    flush(len(lines))

    drafts: list[ChunkDraft] = []
    for section_start, _, section_lines, section_heading in sections:
        buffer: list[str] = []
        buffer_start = section_start
        for offset, line in enumerate(section_lines):
            candidate = "\n".join([*buffer, line]).strip()
            if buffer and len(candidate) > max_chars:
                text = "\n".join(buffer).strip()
                end_line = section_start + offset - 1
                drafts.append(_draft(text, len(drafts), buffer_start, end_line, section_heading))
                buffer = [line]
                buffer_start = section_start + offset
            else:
                buffer.append(line)
        if buffer:
            text = "\n".join(buffer).strip()
            end_line = section_start + len(section_lines) - 1
            drafts.append(_draft(text, len(drafts), buffer_start, end_line, section_heading))
    return drafts


def _draft(text: str, index: int, start: int, end: int, heading: str | None) -> ChunkDraft:
    metadata = {"heading": heading} if heading else {}
    return ChunkDraft(text, index, start, end, len(text.split()), metadata)
