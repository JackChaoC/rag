from __future__ import annotations

import asyncio
import sys

from rag.container import create_container
from rag.resources import container_lifespan, resolve


async def run() -> None:
    container = create_container()
    async with container_lifespan(container):
        broker = await resolve(container.broker)
        dispatcher = await resolve(container.dispatcher)
        failure_handler = await resolve(container.failure_handler)
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
