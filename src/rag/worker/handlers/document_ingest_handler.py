from rag.services.indexing.types.message import IndexMessage, IndexOperation
from rag.use_cases.index_document import IndexDocument


class DocumentIngestHandler:
    def __init__(self, index_document: IndexDocument) -> None:
        self._index_document = index_document

    async def handle(self, message: IndexMessage) -> None:
        if message.operation is not IndexOperation.INGEST:
            raise ValueError(
                f"DocumentIngestHandler cannot handle {message.operation.value!r}"
            )
        await self._index_document.execute(message)
