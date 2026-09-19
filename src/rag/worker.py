from __future__ import annotations

import asyncio
import sys

from rag.config import get_settings
from rag.container import Container
from rag.indexing import IndexingWorker


async def run() -> None:
    container = Container(get_settings())
    await container.start()
    worker = IndexingWorker(container.documents, container.chunks, container.embedder, container.vectors)
    await container.broker.consume(worker.handle, worker.fail)
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


if __name__ == "__main__":
    main()
