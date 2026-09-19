import re


def clean_markdown(content: str) -> str:
    """Normalize Markdown without discarding its structural lines."""
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in content.split("\n")]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip() + "\n" if normalized.strip() else ""
