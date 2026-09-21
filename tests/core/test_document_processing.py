from io import BytesIO

import pytest
from reportlab.pdfgen import canvas

from rag.core.document_processing.chunker import chunk_markdown
from rag.core.document_processing.cleaner import clean_markdown
from rag.core.document_processing.parser import DocumentParser
from rag.infrastructure.database.entities.document import SourceType


def test_cleaner_is_deterministic() -> None:
    source = "# Title  \r\n\r\n\r\nText   \r\n"
    once = clean_markdown(source)
    assert once == "# Title\n\nText\n"
    assert clean_markdown(once) == once


def test_chunker_splits_only_on_h2_and_preserves_one_based_lines() -> None:
    drafts = chunk_markdown("# Document\nintro\n\n## First\nline\n### Detail\nmore\n\n## Second\nlast\n")

    assert [draft.chunk_index for draft in drafts] == [0, 1, 2]
    assert drafts[0].metadata == {}
    assert drafts[1].metadata == {"heading": "First"}
    assert drafts[1].content == "## First\nline\n### Detail\nmore"
    assert (drafts[1].start_line, drafts[1].end_line) == (4, 7)
    assert drafts[2].metadata == {"heading": "Second"}


def test_chunker_structurally_splits_oversized_h2_section() -> None:
    paragraph = "Sentence with useful context. " * 80
    drafts = chunk_markdown(f"## Large\n\n{paragraph}\n\n- final item\n", max_chars=1200)

    assert len(drafts) >= 2
    assert all(len(draft.content) <= 1200 for draft in drafts)
    assert all(draft.metadata == {"heading": "Large"} for draft in drafts)
    assert [draft.chunk_index for draft in drafts] == list(range(len(drafts)))


def test_h1_and_h3_do_not_create_section_boundaries() -> None:
    drafts = chunk_markdown("# Document\nintro\n### Detail\nbody\n")

    assert len(drafts) == 1
    assert drafts[0].content == "# Document\nintro\n### Detail\nbody"


@pytest.mark.asyncio
async def test_parser_reads_markdown_and_pdf() -> None:
    parser = DocumentParser()
    markdown = await parser.parse(b"# Hello", SourceType.MARKDOWN)
    assert markdown.markdown == "# Hello"

    output = BytesIO()
    page = canvas.Canvas(output)
    page.drawString(72, 720, "PDF heading")
    page.save()
    pdf = await parser.parse(output.getvalue(), SourceType.PDF)
    assert "PDF heading" in pdf.markdown
