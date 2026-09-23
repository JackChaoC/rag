from collections.abc import Callable
from dataclasses import dataclass

from rag.use_cases.get_document_chunk import GetDocumentChunk
from rag.use_cases.list_documents import ListDocuments
from rag.use_cases.search_knowledge import SearchKnowledge


@dataclass(frozen=True, slots=True)
class McpDependencies:
    provide_search_knowledge: Callable[[], SearchKnowledge]
    provide_get_document_chunk: Callable[[], GetDocumentChunk]
    provide_list_documents: Callable[[], ListDocuments]
