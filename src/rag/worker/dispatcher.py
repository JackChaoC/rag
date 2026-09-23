from rag.infrastructure.messaging.models import IndexMessage, IndexOperation
from rag.worker.handlers.document_delete_handler import DocumentDeleteHandler
from rag.worker.handlers.document_ingest_handler import DocumentIngestHandler
from rag.worker.handlers.document_reindex_handler import DocumentReindexHandler


class IndexingDispatcher:
    def __init__(
        self,
        document_ingest_handler: DocumentIngestHandler,
        document_reindex_handler: DocumentReindexHandler,
        document_delete_handler: DocumentDeleteHandler,
    ) -> None:
        self._document_ingest_handler = document_ingest_handler
        self._document_reindex_handler = document_reindex_handler
        self._document_delete_handler = document_delete_handler

    async def dispatch(self, routing_key: str, message: IndexMessage) -> None:
        match routing_key:
            case "document.ingest":
                self._require_operation(message, IndexOperation.INGEST)
                await self._document_ingest_handler.handle(message)
            case "document.reindex":
                self._require_operation(message, IndexOperation.REINDEX)
                await self._document_reindex_handler.handle(message)
            case "document.delete":
                self._require_operation(message, IndexOperation.DELETE)
                await self._document_delete_handler.handle(message)
            case _:
                raise ValueError(f"unsupported indexing routing key: {routing_key}")

    @staticmethod
    def _require_operation(
        message: IndexMessage,
        expected: IndexOperation,
    ) -> None:
        if message.operation is not expected:
            raise ValueError(
                f"routing key {expected.routing_key!r} does not match "
                f"message operation {message.operation.value!r}"
            )
