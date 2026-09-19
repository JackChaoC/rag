import asyncio

import uvicorn

from rag.interfaces.http.app import create_app

app = create_app()


def selector_loop_factory() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop()


def main() -> None:
    uvicorn.run(
        "rag.main:app", host="127.0.0.1", port=8000, reload=False,
        loop="rag.main:selector_loop_factory",
    )


if __name__ == "__main__":
    main()
