from rag.services.indexing.types.message import IndexMessage, IndexOperation
from rag.use_cases.index_document_use_case import IndexDocumentUseCase


class DocumentReindexHandler:
    def __init__(self, indexDocumentUseCase: IndexDocumentUseCase) -> None:
        self.indexDocumentUseCase = indexDocumentUseCase

    async def handle(self, message: IndexMessage) -> None:
        if message.operation is not IndexOperation.REINDEX:
            raise ValueError(
                f"DocumentReindexHandler cannot handle {message.operation.value!r}"
            )
        await self.indexDocumentUseCase.execute(message)
