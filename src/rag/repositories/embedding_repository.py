from llama_index.core.ingestion import IngestionPipeline
from llama_index.embeddings.ollama import OllamaEmbedding


class EmbeddingRepository:
    def __init__(self, ollamaResource: OllamaEmbedding):
        self.ollamaResource = ollamaResource

    async def embedNodes(self, nodes):
        pipeline = IngestionPipeline(
            transformations=[self.ollamaResource], disable_cache=True
        )
        return await pipeline.arun(nodes=nodes)
