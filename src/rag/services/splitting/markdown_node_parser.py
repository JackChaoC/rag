import re
from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid5

from llama_index.core.node_parser import NodeParser
from llama_index.core.schema import (
    BaseNode,
    Document as LlamaIndexDocument,
    NodeRelationship,
    RelatedNodeInfo,
    TextNode,
)

from rag.services.splitting.chunker import chunk_markdown


class MarkdownNodeParser(NodeParser):
    max_chars: int = 1200

    def get_nodes_from_documents(
        self,
        llamaindex_documents: Sequence[LlamaIndexDocument],
        show_progress: bool = False,
        **kwargs: Any,
    ) -> list[BaseNode]:
        return super().get_nodes_from_documents(
            llamaindex_documents,
            show_progress=show_progress,
            **kwargs,
        )

    def _parse_nodes(self, nodes, show_progress=False, **kwargs):
        output = []
        counts = {}
        for document in nodes:
            documentId = str(document.metadata.get("document_id", document.id_))
            # H1 is metadata only; H2 boundaries and character splitting stay unchanged.
            heading = None
            fence = None
            for line in document.text.splitlines():
                marker = re.match(r"^\s*(`{3,}|~{3,})", line)
                if marker:
                    if fence is None:
                        fence = marker.group(1)[0]
                    elif marker.group(1)[0] == fence:
                        fence = None
                    continue
                if fence is None and (match := re.match(r"^#\s+(.+?)\s*#*\s*$", line)):
                    heading = match.group(1)
                    break
            for draft in chunk_markdown(document.text, self.max_chars):
                index = counts.get(documentId, 0)
                counts[documentId] = index + 1
                metadata = dict(document.metadata)
                metadata.update(
                    document_id=documentId,
                    chunk_index=index,
                    heading_h1=heading or "",
                    heading_h2=draft.metadata.get("heading", ""),
                    start_line=draft.start_line,
                    end_line=draft.end_line,
                )
                node = TextNode(
                    id_=str(uuid5(UUID(documentId), f"{metadata['version']}:{index}")),
                    text=draft.content,
                    metadata=metadata,
                    relationships={
                        NodeRelationship.SOURCE: RelatedNodeInfo(node_id=documentId)
                    },
                    excluded_embed_metadata_keys=[
                        key
                        for key in metadata
                        if key not in {"title", "heading_h1", "heading_h2"}
                    ],
                )
                output.append(node)
        return output
