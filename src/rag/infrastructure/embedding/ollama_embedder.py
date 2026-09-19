from __future__ import annotations

from collections.abc import Sequence

import httpx


class OllamaEmbedder:
    def __init__(self, base_url: str, model: str, timeout: float = 120.0, num_gpu: int = 0) -> None:
        self._model = model
        self._num_gpu = num_gpu
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout)

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.post(
            "/api/embed",
            json={
                "model": self._model,
                "input": list(texts),
                "keep_alive": 0,
                "options": {"num_gpu": self._num_gpu},
            },
        )
        response.raise_for_status()
        embeddings = response.json().get("embeddings")
        if not embeddings or len(embeddings) != len(texts) or any(not vector for vector in embeddings):
            raise RuntimeError("Ollama returned invalid embeddings")
        dimension = len(embeddings[0])
        if any(len(vector) != dimension for vector in embeddings):
            raise RuntimeError("Ollama returned inconsistent embedding dimensions")
        return embeddings

    async def aclose(self) -> None:
        await self._client.aclose()
