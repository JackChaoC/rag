from rag.services.indexing.types.message import IndexMessage, IndexOperation
from rag.use_cases.delete_document_index import DeleteDocumentIndex


class DocumentDeleteHandler:
    def __init__(self, delete_document_index: DeleteDocumentIndex) -> None:
        self._delete_document_index = delete_document_index

    async def handle(self, message: IndexMessage) -> None:
        if message.operation is not IndexOperation.DELETE:
            raise ValueError(
                f"DocumentDeleteHandler cannot handle {message.operation.value!r}"
            )

        await self._delete_document_index.execute(message)
