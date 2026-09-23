from rag.infrastructure.messaging.models import IndexMessage, IndexOperation
from rag.worker.document_indexer import DocumentIndexer


class DocumentReindexHandler:
    def __init__(self, indexer: DocumentIndexer) -> None:
        self._indexer = indexer

    async def handle(self, message: IndexMessage) -> None:
        if message.operation is not IndexOperation.REINDEX:
            raise ValueError(
                f"DocumentReindexHandler cannot handle {message.operation.value!r}"
            )
        await self._indexer.index(message)
