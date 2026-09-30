from rag.services.publisher.types.message import IndexMessage
from rag.use_cases.finalize_index_failure_use_case import FinalizeIndexFailureUseCase


class FailureHandler:
    def __init__(
        self, finalizeIndexFailureUseCase: FinalizeIndexFailureUseCase
    ) -> None:
        self.finalizeIndexFailureUseCase = finalizeIndexFailureUseCase

    async def handle(self, message: IndexMessage, error: Exception) -> None:
        await self.finalizeIndexFailureUseCase.execute(message, error)
