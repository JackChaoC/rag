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


def test_chunker_preserves_heading_and_one_based_lines() -> None:
    drafts = chunk_markdown("# First\nline\n\n## Second\nmore\n")
    assert [draft.chunk_index for draft in drafts] == [0, 1]
    assert (drafts[0].start_line, drafts[0].end_line) == (1, 3)
    assert drafts[1].metadata == {"heading": "Second"}


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
