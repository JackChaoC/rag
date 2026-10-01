from llama_index.core.ingestion import IngestionPipeline
from rag.resources.ollama.client import OllamaResource


class EmbeddingRepository:
    def __init__(self, ollamaResource: OllamaResource):
        self.ollamaResource = ollamaResource

    async def embedNodes(self, nodes):
        pipeline = IngestionPipeline(
            transformations=[self.ollamaResource], disable_cache=True
        )
        return await pipeline.arun(nodes=nodes)

    async def healthcheck(self) -> bool:
        return await self.ollamaResource.healthcheck()
