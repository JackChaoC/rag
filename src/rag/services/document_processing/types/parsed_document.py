from dataclasses import dataclass

from rag.services.documents.types.document import SourceType


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    markdown: str
    source_type: SourceType
