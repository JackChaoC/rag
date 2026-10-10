from unittest.mock import AsyncMock
from types import SimpleNamespace

from rag.resources.ollama.client import OllamaResource


async def test_ollama_chooses_device_without_num_gpu_override():
    resource = OllamaResource('http://127.0.0.1:11434', 'qwen3-embedding:8b')
    try:
        resource._async_client.embed = AsyncMock(return_value=SimpleNamespace(embeddings=[[1.0, 2.0]]))
        await resource._aget_text_embeddings(['hello'])
        kwargs = resource._async_client.embed.call_args.kwargs
        assert 'num_gpu' not in (kwargs.get('options') or {})
        assert kwargs['keep_alive'] == '5m'
    finally:
        await resource.close()
