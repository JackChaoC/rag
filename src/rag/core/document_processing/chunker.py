from __future__ import annotations

import re
from dataclasses import dataclass


_H2 = re.compile(r"^##(?:[ \t]+(?P<title>.*?)[ \t]*|[ \t]*)$")
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?。！？])(?:\s+|(?=\S))")


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    content: str
    chunk_index: int
    start_line: int
    end_line: int
    token_count: int
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class _Section:
    lines: list[tuple[int, str]]
    heading: str | None


@dataclass(frozen=True, slots=True)
class _Piece:
    text: str
    start_line: int
    end_line: int
    separator: str = "\n"


def chunk_markdown(content: str, max_chars: int = 1200) -> list[ChunkDraft]:
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")

    drafts: list[ChunkDraft] = []
    for section in _split_sections(content.splitlines()):
        for text, start_line, end_line in _split_section(section.lines, max_chars):
            metadata = {"heading": section.heading} if section.heading else {}
            drafts.append(
                ChunkDraft(
                    content=text,
                    chunk_index=len(drafts),
                    start_line=start_line,
                    end_line=end_line,
                    token_count=len(text.split()),
                    metadata=metadata,
                )
            )
    return drafts


def _split_sections(lines: list[str]) -> list[_Section]:
    sections: list[_Section] = []
    current: list[tuple[int, str]] = []
    heading: str | None = None

    def flush() -> None:
        nonlocal current
        if any(line.strip() for _, line in current):
            sections.append(_Section(current, heading))
        current = []

    for line_no, line in enumerate(lines, start=1):
        match = _H2.match(line)
        if match:
            flush()
            heading = (match.group("title") or "").rstrip("#").strip() or None
        current.append((line_no, line))
    flush()
    return sections


def _split_section(
    lines: list[tuple[int, str]], max_chars: int,
) -> list[tuple[str, int, int]]:
    # Leave room for a heading or short preceding block when packing pieces.
    piece_limit = max_chars - min(128, max_chars // 4)
    pieces: list[_Piece] = []
    for block in _semantic_blocks(lines):
        pieces.extend(_split_block(block, piece_limit))

    chunks: list[tuple[str, int, int]] = []
    buffer: list[_Piece] = []
    for piece in pieces:
        separator = piece.separator if buffer else ""
        candidate = f"{_join(buffer)}{separator}{piece.text}".strip()
        if buffer and len(candidate) > max_chars:
            chunks.append((_join(buffer), buffer[0].start_line, buffer[-1].end_line))
            buffer = [piece]
        else:
            buffer.append(piece)
    if buffer:
        chunks.append((_join(buffer), buffer[0].start_line, buffer[-1].end_line))
    return chunks


def _semantic_blocks(lines: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    blocks: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    fence: str | None = None

    def flush() -> None:
        nonlocal current
        if any(line.strip() for _, line in current):
            blocks.append(current)
        current = []

    for item in lines:
        _, line = item
        marker = _FENCE.match(line)
        if fence is not None:
            current.append(item)
            if marker and marker.group(1).startswith(fence[0]):
                fence = None
                flush()
            continue
        if marker:
            flush()
            fence = marker.group(1)
            current.append(item)
        elif not line.strip():
            flush()
        else:
            current.append(item)
    flush()
    return blocks


def _split_block(block: list[tuple[int, str]], limit: int) -> list[_Piece]:
    text = "\n".join(line for _, line in block).strip()
    if len(text) <= limit:
        return [_Piece(text, block[0][0], block[-1][0], "\n\n")]

    pieces: list[_Piece] = []
    for line_no, line in block:
        fragments = _split_long_text(line.strip(), limit)
        for index, fragment in enumerate(fragments):
            if not fragment:
                continue
            separator = "\n" if index == 0 else " "
            pieces.append(_Piece(fragment, line_no, line_no, separator))
    if pieces:
        first = pieces[0]
        pieces[0] = _Piece(first.text, first.start_line, first.end_line, "\n\n")
    return pieces


def _split_long_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]

    fragments: list[str] = []
    buffer = ""
    for sentence in filter(None, _SENTENCE_BOUNDARY.split(text)):
        candidate = f"{buffer} {sentence}".strip()
        if buffer and len(candidate) > limit:
            fragments.append(buffer)
            buffer = sentence
        else:
            buffer = candidate
        while len(buffer) > limit:
            fragments.append(buffer[:limit].rstrip())
            buffer = buffer[limit:].lstrip()
    if buffer:
        fragments.append(buffer)
    return fragments


def _join(pieces: list[_Piece]) -> str:
    if not pieces:
        return ""
    text = pieces[0].text
    for piece in pieces[1:]:
        text = f"{text}{piece.separator}{piece.text}"
    return text.strip()
