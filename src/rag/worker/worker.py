from __future__ import annotations

import asyncio
import sys

from rag.config import get_settings
from rag.container import Container
from rag.worker.factory import create_worker_services


async def run() -> None:
    container = Container(get_settings())
    await container.start()
    services = create_worker_services(
        container.documents,
        container.chunks,
        container.embedder,
        container.vectors,
    )
    await container.broker.consume(
        services.dispatcher.dispatch,
        on_dead=services.failure_handler.handle,
        on_retry=services.retry_handler.handle,
    )
    try:
        await asyncio.Future()
    finally:
        await container.close()


def main() -> None:
    try:
        if sys.platform == "win32":
            with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                runner.run(run())
        else:
            asyncio.run(run())
    except KeyboardInterrupt:
        pass
