from rag.services.indexing.types.message import IndexMessage, IndexOperation
from rag.use_cases.delete_document_index_use_case import DeleteDocumentIndexUseCase


class DocumentDeleteHandler:
    def __init__(self, deleteDocumentIndexUseCase: DeleteDocumentIndexUseCase) -> None:
        self.deleteDocumentIndexUseCase = deleteDocumentIndexUseCase

    async def handle(self, message: IndexMessage) -> None:
        if message.operation is not IndexOperation.DELETE:
            raise ValueError(
                f"DocumentDeleteHandler cannot handle {message.operation.value!r}"
            )

        await self.deleteDocumentIndexUseCase.execute(message)
