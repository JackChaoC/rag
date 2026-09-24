from __future__ import annotations

import asyncio
import sys

from rag.containers import create_container
from rag.containers.resources import container_lifespan, resolve


async def run() -> None:
    container = create_container()
    async with container_lifespan(container):
        broker = await resolve(container.resources.broker)
        dispatcher = await resolve(container.worker.dispatcher)
        failure_handler = await resolve(container.worker.failure_handler)
        await broker.consume(dispatcher.dispatch, failure_handler.handle)
        await asyncio.Future()


def main() -> None:
    try:
        if sys.platform == "win32":
            with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                runner.run(run())
        else:
            asyncio.run(run())
    except KeyboardInterrupt:
        pass
