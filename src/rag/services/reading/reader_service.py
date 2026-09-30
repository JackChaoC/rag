import asyncio
from pathlib import Path

from llama_index.core import Document as LlamaDocument
from llama_index.core import SimpleDirectoryReader
from llama_index.readers.file import PDFReader


class ReaderService:
    async def read(self, path: Path, documentId, metadata: dict) -> list[LlamaDocument]:
        # Read Markdown verbatim: generic MarkdownReader can remove heading markers.
        def load():
            if path.suffix.lower() == ".pdf":
                parts = SimpleDirectoryReader(
                    input_files=[str(path)],
                    file_extractor={".pdf": PDFReader(return_full_document=True)},
                    raise_on_error=True,
                ).load_data()
                text = "\n\n".join(part.text for part in parts)
            else:
                text = path.read_text(encoding="utf-8-sig")
            text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
            if not text:
                raise ValueError("parsed document is empty")
            return [LlamaDocument(id_=str(documentId), text=text, metadata=metadata)]

        return await asyncio.to_thread(load)
