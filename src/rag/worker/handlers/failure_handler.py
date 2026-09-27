from rag.services.indexing.types.message import IndexMessage
from rag.use_cases.finalize_index_failure import FinalizeIndexFailure


class FailureHandler:
    def __init__(self, finalize_index_failure: FinalizeIndexFailure) -> None:
        self._finalize_index_failure = finalize_index_failure

    async def handle(self, message: IndexMessage, error: Exception) -> None:
        await self._finalize_index_failure.execute(message, error)
