from qdrant_client import AsyncQdrantClient


def create_qdrant_client(url: str) -> AsyncQdrantClient:
    return AsyncQdrantClient(url=url)
