from rag.services.indexing.types.message import IndexMessage, IndexOperation
from rag.use_cases.index_document_use_case import IndexDocumentUseCase


class DocumentIngestHandler:
    def __init__(self, indexDocumentUseCase: IndexDocumentUseCase) -> None:
        self.indexDocumentUseCase = indexDocumentUseCase

    async def handle(self, message: IndexMessage) -> None:
        if message.operation is not IndexOperation.INGEST:
            raise ValueError(
                f"DocumentIngestHandler cannot handle {message.operation.value!r}"
            )
        await self.indexDocumentUseCase.execute(message)
