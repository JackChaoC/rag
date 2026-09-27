from collections.abc import Callable

import httpx
from qdrant_client import AsyncQdrantClient

from rag.resources.database.client import Database
from rag.resources.messaging.broker import RabbitBroker


class HealthRepository:
    def __init__(
        self,
        database: Database,
        broker: RabbitBroker,
        qdrant: AsyncQdrantClient,
        http_client_factory: Callable[[], httpx.AsyncClient],
    ) -> None:
        self._database = database
        self._broker = broker
        self._qdrant = qdrant
        self._http_client_factory = http_client_factory

    async def check_all(self) -> dict[str, bool]:
        return {
            "postgresql": await self._check_postgresql(),
            "rabbitmq": await self._check_rabbitmq(),
            "qdrant": await self._check_qdrant(),
            "ollama": await self._check_ollama(),
        }

    async def _check_postgresql(self) -> bool:
        try:
            return await self._database.ping()
        except Exception:
            return False

    async def _check_rabbitmq(self) -> bool:
        try:
            return await self._broker.ping()
        except Exception:
            return False

    async def _check_qdrant(self) -> bool:
        try:
            await self._qdrant.get_collections()
        except Exception:
            return False
        return True

    async def _check_ollama(self) -> bool:
        try:
            async with self._http_client_factory() as client:
                return (await client.get("/api/tags")).is_success
        except Exception:
            return False
