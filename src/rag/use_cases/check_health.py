from __future__ import annotations

from rag.services.health.health_service import HealthService
from rag.services.health.types.health_status import HealthStatus


class CheckHealth:
    def __init__(
        self,
        health: HealthService,
    ) -> None:
        self._health = health

    async def execute(self) -> HealthStatus:
        return await self._health.check()
