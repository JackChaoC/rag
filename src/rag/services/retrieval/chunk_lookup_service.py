from uuid import UUID

from rag.repositories.vector_repository import VectorRepository
from rag.services.common.errors import NotFoundError
from rag.services.documents.types.hydrated_chunk import HydratedChunk


def chunkDetail(node):
    metadata = {k: v for k, v in node.metadata.items() if k != "source_uri"}
    return HydratedChunk(
        UUID(node.node_id),
        UUID(metadata["document_id"]),
        node.text,
        metadata.get("file_url") or f"/v1/files/{metadata['document_id']}",
        metadata.get("title") or None,
        metadata.get("start_line"),
        metadata.get("end_line"),
        metadata,
    )


class ChunkLookupService:
    def __init__(self, vectorRepository: VectorRepository):
        self.vectorRepository = vectorRepository

    async def listChunks(self, documentId: UUID):
        return [
            chunkDetail(node)
            for node in await self.vectorRepository.listChunks(documentId)
        ]

    async def getChunkDetail(self, chunkId: UUID):
        node = await self.vectorRepository.getChunkDetail(chunkId)
        if node is None:
            raise NotFoundError("chunk not found")
        return chunkDetail(node)
