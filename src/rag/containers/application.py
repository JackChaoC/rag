from dependency_injector import containers, providers

from rag.config import Settings, get_settings
from rag.containers.repositories import Repositories
from rag.containers.resources import Resources
from rag.containers.services import Services
from rag.containers.use_cases import UseCases
from rag.containers.worker import Worker


class ApplicationContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.Container(Resources, config=config)
    repositories = providers.Container(Repositories, resources=resources, config=config)
    services = providers.Container(Services, repositories=repositories, config=config)
    use_cases = providers.Container(
        UseCases,
        services=services,
    )
    worker = providers.Container(Worker, use_cases=use_cases)


def create_container(settings: Settings | None = None) -> ApplicationContainer:
    container = ApplicationContainer()
    container.config.from_dict((settings or get_settings()).model_dump())
    return container
