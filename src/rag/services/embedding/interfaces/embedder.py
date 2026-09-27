from typing import Protocol, Sequence


class Embedder(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...
