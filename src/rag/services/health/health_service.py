from rag.repositories.health_repository import HealthRepository
from rag.services.health.types.health_status import HealthStatus


class HealthService:
    def __init__(self, healthRepository: HealthRepository) -> None:
        self.healthRepository = healthRepository

    async def check(self) -> HealthStatus:
        checks = await self.healthRepository.check_all()
        return HealthStatus(ready=all(checks.values()), dependencies=checks)
