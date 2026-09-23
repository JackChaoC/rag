import json

import httpx
import pytest

from rag.infrastructure.embedding.ollama_embedder import OllamaEmbedder


@pytest.mark.asyncio
async def test_ollama_controls_device_and_keeps_model_loaded_for_five_minutes() -> None:
    requests: list[httpx.Request] = []

    async def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"embeddings": [[1.0, 0.0], [0.0, 1.0]]},
        )

    embedder = OllamaEmbedder("http://ollama.test", "qwen3-embedding:8b")
    await embedder._client.aclose()
    embedder._client = httpx.AsyncClient(
        base_url="http://ollama.test",
        transport=httpx.MockTransport(respond),
    )

    try:
        assert await embedder.embed(["hello", "world"]) == [
            [1.0, 0.0],
            [0.0, 1.0],
        ]
    finally:
        await embedder.aclose()

    payload = json.loads(requests[0].content)
    assert payload == {
        "model": "qwen3-embedding:8b",
        "input": ["hello", "world"],
        "keep_alive": "5m",
    }
