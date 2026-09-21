from __future__ import annotations


def document_embedding_text(
    body: str, *, document_title: str | None = None, section_heading: str | None = None,
) -> str:
    """Build the semantic text embedded for one document chunk."""
    parts: list[str] = []
    if document_title and document_title.strip():
        parts.append(f"# {document_title.strip()}")
    if section_heading and section_heading.strip():
        parts.append(f"## {section_heading.strip()}")

    normalized_body = body.strip()
    if section_heading:
        lines = normalized_body.splitlines()
        if lines and _is_same_h2(lines[0], section_heading):
            normalized_body = "\n".join(lines[1:]).strip()
    if normalized_body:
        parts.append(normalized_body)
    return "\n\n".join(parts)


def _is_same_h2(line: str, heading: str) -> bool:
    if not line.startswith("## ") or line.startswith("###"):
        return False
    return line[3:].rstrip("#").strip() == heading.strip()
