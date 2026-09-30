from rag.services.health.health_service import HealthService


class CheckHealthUseCase:
    def __init__(self, healthService: HealthService) -> None:
        self.healthService = healthService

    async def execute(self):
        return await self.healthService.check()
