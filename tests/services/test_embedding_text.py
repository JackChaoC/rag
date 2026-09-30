from uuid import uuid4

from llama_index.core import Document
from llama_index.core.schema import MetadataMode, NodeRelationship

from rag.services.splitting.chunker import chunk_markdown
from rag.services.splitting.markdown_node_parser import MarkdownNodeParser


def test_node_parser_keeps_main_algorithm_and_global_index():
    documentId = str(uuid4())
    text = "# Guide\nintro\n\n## Setup\n" + "Some sentence. " * 200 + "\n## End\nlast"
    document = Document(
        id_=documentId,
        text=text,
        metadata={
            "document_id": documentId,
            "version": 1,
            "title": "Manual",
            "chunk_index": 999,
        },
    )
    parser = MarkdownNodeParser()
    nodes = parser.get_nodes_from_documents([document])
    drafts = chunk_markdown(text)
    assert [n.text for n in nodes] == [d.content for d in drafts]
    assert [n.metadata["chunk_index"] for n in nodes] == list(range(len(nodes)))
    assert all(n.metadata["heading_h1"] == "Guide" for n in nodes)
    assert nodes[-1].metadata["heading_h2"] == "End"
    assert nodes[-1].relationships[NodeRelationship.SOURCE].node_id == documentId
    assert [n.id_ for n in nodes] == [
        n.id_ for n in parser.get_nodes_from_documents([document])
    ]
    embedded = nodes[-1].get_content(metadata_mode=MetadataMode.EMBED)
    assert "heading_h1: Guide" in embedded and "heading_h2: End" in embedded
    assert "version:" not in embedded and "document_id:" not in embedded
    assert "chunk_index:" not in embedded
    document.metadata["version"] = 2
    assert nodes[0].id_ != parser.get_nodes_from_documents([document])[0].id_


def test_code_fence_heading_is_not_document_heading():
    doc = Document(
        id_=str(uuid4()),
        text="```md\n# Fake\n```\n# Real\n## Section\nbody",
        metadata={"version": 1},
    )
    nodes = MarkdownNodeParser().get_nodes_from_documents([doc])
    assert all(n.metadata["heading_h1"] == "Real" for n in nodes)
