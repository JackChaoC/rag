from rag.repositories.health_repository import HealthRepository
from rag.services.health.types.health_status import HealthStatus


class HealthService:
    def __init__(self, health: HealthRepository) -> None:
        self._health = health

    async def check(self) -> HealthStatus:
        checks = await self._health.check_all()
        return HealthStatus(ready=all(checks.values()), dependencies=checks)
