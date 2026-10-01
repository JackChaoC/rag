import asyncio
from uuid import UUID

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import models


class VectorRepository:
    def __init__(self, qdrantResource, ollamaResource, collection: str):
        self.qdrantResource = qdrantResource
        self.ollamaResource = ollamaResource
        self.collection = collection
        self._writeLock = asyncio.Lock()
        self.vectorStore = QdrantVectorStore(
            collection_name=collection, aclient=qdrantResource
        )

    async def healthcheck(self) -> bool:
        await self.qdrantResource.get_collections()
        return True

    async def add(self, nodes):
        if not nodes:
            return
        # Serialize first-collection creation; a removed collection can be rebuilt.
        async with self._writeLock:
            if not await self.qdrantResource.collection_exists(self.collection):
                self.vectorStore = QdrantVectorStore(
                    collection_name=self.collection, aclient=self.qdrantResource
                )
            await self.vectorStore.async_add(nodes)

    async def deleteDocument(self, documentId: UUID):
        if await self.qdrantResource.collection_exists(self.collection):
            await self.vectorStore.adelete(str(documentId))

    async def listChunks(self, documentId: UUID):
        if not await self.qdrantResource.collection_exists(self.collection):
            return []
        nodes, offset = [], None
        while True:
            points, offset = await self.qdrantResource.scroll(
                collection_name=self.collection,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=str(documentId)),
                        )
                    ]
                ),
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            nodes.extend(self.vectorStore.parse_to_query_result(points).nodes)
            if offset is None:
                break
        return sorted(nodes, key=lambda node: node.metadata["chunk_index"])

    async def getChunkDetail(self, chunkId: UUID):
        if not await self.qdrantResource.collection_exists(self.collection):
            return None
        nodes = await self.vectorStore.aget_nodes(node_ids=[str(chunkId)])
        return nodes[0] if nodes else None

    async def query(self, text: str, top_k: int = 5) -> list[NodeWithScore]:
        if not await self.qdrantResource.collection_exists(self.collection):
            return []
        index = VectorStoreIndex.from_vector_store(
            self.vectorStore, embed_model=self.ollamaResource
        )
        return await index.as_retriever(similarity_top_k=top_k).aretrieve(text)
