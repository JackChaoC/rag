from __future__ import annotations

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path

from markitdown import MarkItDown

from rag.infrastructure.database.entities.document import SourceType


class UnsupportedSourceType(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    markdown: str
    source_type: SourceType


class DocumentParser:
    _enabled = {SourceType.MARKDOWN, SourceType.TEXT, SourceType.PDF}

    def __init__(self) -> None:
        self._markitdown = MarkItDown(enable_plugins=False)

    async def parse(self, data: bytes, source_type: SourceType) -> ParsedDocument:
        if source_type not in self._enabled:
            raise UnsupportedSourceType(f"unsupported source type: {source_type.value}")
        if source_type in {SourceType.MARKDOWN, SourceType.TEXT}:
            return ParsedDocument(data.decode("utf-8"), source_type)
        markdown = await asyncio.to_thread(self._convert_file, data, ".pdf")
        return ParsedDocument(markdown, source_type)

    def _convert_file(self, data: bytes, suffix: str) -> str:
        path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as stream:
                stream.write(data)
                path = Path(stream.name)
            result = self._markitdown.convert(str(path))
            markdown = getattr(result, "markdown", None) or getattr(result, "text_content", None)
            if not markdown:
                raise ValueError("MarkItDown returned empty content")
            return str(markdown)
        finally:
            if path is not None:
                path.unlink(missing_ok=True)
