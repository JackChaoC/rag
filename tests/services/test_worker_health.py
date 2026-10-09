from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from rag.resources.rabbitmq.broker import RabbitMQResource
from rag.services.health.health_service import HealthService


@pytest.mark.parametrize('messages,consumers,healthy', [(1, 1, True), (0, 1, False), (1, 0, False), (0, 0, False), (1, 2, True)])
async def test_worker_requires_fresh_heartbeat_and_consumer(messages, consumers, healthy):
    broker = RabbitMQResource('amqp://unused', (1, 5, 30))
    broker.channel = SimpleNamespace(declare_queue=AsyncMock(side_effect=[
        SimpleNamespace(declaration_result=SimpleNamespace(message_count=messages)),
        SimpleNamespace(declaration_result=SimpleNamespace(consumer_count=consumers)),
    ]))
    assert await broker.worker_healthcheck() is healthy


@pytest.mark.parametrize('worker_result', [False, RuntimeError('broker unavailable')])
async def test_worker_failure_makes_service_unready(worker_result):
    dependency = SimpleNamespace(healthcheck=AsyncMock(return_value=True))
    tasks = SimpleNamespace(healthcheck=AsyncMock(return_value=True), worker_healthcheck=AsyncMock())
    if isinstance(worker_result, Exception):
        tasks.worker_healthcheck.side_effect = worker_result
    else:
        tasks.worker_healthcheck.return_value = worker_result
    status = await HealthService(dependency, tasks, dependency, dependency).check()
    assert status.ready is False
    assert status.dependencies['worker'] is False
    assert status.dependencies['rabbitmq'] is True


async def test_heartbeat_requires_registered_consumer():
    broker = RabbitMQResource('amqp://unused', (1, 5, 30))
    exchange = SimpleNamespace(publish=AsyncMock())
    broker.channel = SimpleNamespace(default_exchange=exchange)
    with pytest.raises(RuntimeError, match='consumer'):
        await broker.publish_worker_heartbeat()
    broker._consumer_tag = 'worker'
    await broker.publish_worker_heartbeat()
    exchange.publish.assert_awaited_once()
    assert exchange.publish.call_args.kwargs['routing_key'] == f'{broker.namespace}.worker-heartbeat'
