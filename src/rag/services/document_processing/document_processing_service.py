from uuid import uuid4

from rag.services.document_processing.chunker import chunk_markdown
from rag.services.document_processing.cleaner import clean_markdown
from rag.services.document_processing.parser import DocumentParser
from rag.services.document_processing.types.chunk import ChunkDraft
from rag.services.documents.types.chunk import Chunk
from rag.services.documents.types.document import Document, SourceType


class DocumentProcessingService:
    def __init__(self, parser: DocumentParser) -> None:
        self._parser = parser

    async def parse_and_clean(self, data: bytes, source_type: SourceType) -> str:
        parsed = await self._parser.parse(data, source_type)
        content = clean_markdown(parsed.markdown)
        if not content:
            raise ValueError("parsed document is empty")
        return content

    def chunk(self, content: str) -> list[ChunkDraft]:
        return chunk_markdown(content)

    def build_chunks(self, document: Document) -> list[Chunk]:
        return [
            Chunk(
                uuid4(),
                document.id,
                document.current_version,
                draft.chunk_index,
                draft.content,
                draft.start_line,
                draft.end_line,
                draft.token_count,
                draft.metadata,
            )
            for draft in self.chunk(document.content)
        ]
