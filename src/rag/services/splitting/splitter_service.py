from collections.abc import Sequence

from llama_index.core import Document as LlamaIndexDocument
from llama_index.core.schema import BaseNode

from rag.services.splitting.markdown_node_parser import MarkdownNodeParser


class SplitterService:
    def __init__(self, markdownNodeParser: MarkdownNodeParser):
        self.markdownNodeParser = markdownNodeParser

    def split(
        self, llamaindex_documents: Sequence[LlamaIndexDocument]
    ) -> list[BaseNode]:
        return self.markdownNodeParser.get_nodes_from_documents(
            llamaindex_documents
        )
