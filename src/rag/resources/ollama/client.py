from llama_index.embeddings.ollama import OllamaEmbedding


class OllamaResource(OllamaEmbedding):
    def __init__(self, url: str, model: str, num_gpu: int) -> None:
        super().__init__(
            model_name=model,
            base_url=url,
            ollama_additional_kwargs={"num_gpu": num_gpu},
            client_kwargs={"timeout": 120},
        )

    async def healthcheck(self) -> bool:
        response = await self._async_client._client.get("/api/tags", timeout=2)
        return response.is_success

    async def close(self) -> None:
        # OllamaEmbedding exposes no public close; this resource owns its SDK clients.
        self._client._client.close()
        await self._async_client._client.aclose()
