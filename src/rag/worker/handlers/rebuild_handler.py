from rag.use_cases.rebuild_index import RebuildIndex


class RebuildHandler:
    def __init__(self, rebuild_index: RebuildIndex) -> None:
        self._rebuild_index = rebuild_index

    async def handle(self) -> int:
        return await self._rebuild_index.execute()
