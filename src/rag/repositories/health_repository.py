from collections.abc import Callable

import httpx
from qdrant_client import AsyncQdrantClient

from rag.resources.database.client import DatabaseResource
from rag.resources.messaging.broker import RabbitBrokerResource


class HealthRepository:
    def __init__(
        self,
        databaseResource: DatabaseResource,
        brokerResource: RabbitBrokerResource,
        qdrantResource: AsyncQdrantClient,
        httpClientFactory: Callable[[], httpx.AsyncClient],
    ) -> None:
        self.databaseResource = databaseResource
        self.brokerResource = brokerResource
        self.qdrantResource = qdrantResource
        self.httpClientFactory = httpClientFactory

    async def check_all(self) -> dict[str, bool]:
        return {
            "postgresql": await self._check_postgresql(),
            "rabbitmq": await self._check_rabbitmq(),
            "qdrant": await self._check_qdrant(),
            "ollama": await self._check_ollama(),
        }

    async def _check_postgresql(self) -> bool:
        try:
            return await self.databaseResource.ping()
        except Exception:
            return False

    async def _check_rabbitmq(self) -> bool:
        try:
            return await self.brokerResource.ping()
        except Exception:
            return False

    async def _check_qdrant(self) -> bool:
        try:
            await self.qdrantResource.get_collections()
        except Exception:
            return False
        return True

    async def _check_ollama(self) -> bool:
        try:
            async with self.httpClientFactory() as client:
                return (await client.get("/api/tags")).is_success
        except Exception:
            return False
