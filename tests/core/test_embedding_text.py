from rag.core.embedding.text import document_embedding_text


def test_embedding_text_combines_document_title_heading_and_body() -> None:
    result = document_embedding_text(
        "## Migrations\nAlembic manages revisions.",
        document_title="PostgreSQL Guide",
        section_heading="Migrations",
    )

    assert result == "# PostgreSQL Guide\n\n## Migrations\n\nAlembic manages revisions."


def test_embedding_text_keeps_plain_body_unchanged_without_titles() -> None:
    assert document_embedding_text("plain body\n") == "plain body"
