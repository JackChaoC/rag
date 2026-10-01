from qdrant_client import AsyncQdrantClient


class QdrantResource(AsyncQdrantClient):
    """Project-owned Qdrant client resource."""

