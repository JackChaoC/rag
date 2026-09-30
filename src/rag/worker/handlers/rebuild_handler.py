from rag.use_cases.rebuild_index_use_case import RebuildIndexUseCase


class RebuildHandler:
    def __init__(self, rebuildIndexUseCase: RebuildIndexUseCase) -> None:
        self.rebuildIndexUseCase = rebuildIndexUseCase

    async def handle(self) -> int:
        return await self.rebuildIndexUseCase.execute()
