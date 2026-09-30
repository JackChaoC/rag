from rag.services.indexing.types.message import IndexMessage, IndexOperation
from rag.worker.handlers.document_delete_handler import DocumentDeleteHandler
from rag.worker.handlers.document_ingest_handler import DocumentIngestHandler
from rag.worker.handlers.document_reindex_handler import DocumentReindexHandler


class IndexingDispatcher:
    def __init__(
        self,
        documentIngestHandler: DocumentIngestHandler,
        documentReindexHandler: DocumentReindexHandler,
        documentDeleteHandler: DocumentDeleteHandler,
    ) -> None:
        self.documentIngestHandler = documentIngestHandler
        self.documentReindexHandler = documentReindexHandler
        self.documentDeleteHandler = documentDeleteHandler

    async def dispatch(self, routing_key: str, message: IndexMessage) -> None:
        match routing_key:
            case "document.ingest":
                self._require_operation(message, IndexOperation.INGEST)
                await self.documentIngestHandler.handle(message)
            case "document.reindex":
                self._require_operation(message, IndexOperation.REINDEX)
                await self.documentReindexHandler.handle(message)
            case "document.delete":
                self._require_operation(message, IndexOperation.DELETE)
                await self.documentDeleteHandler.handle(message)
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
