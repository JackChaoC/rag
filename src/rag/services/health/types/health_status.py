from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthStatus:
    ready: bool
    dependencies: dict[str, bool]
