import argparse
import asyncio

import uvicorn

from rag.api.http.app import create_app

app = create_app()


def selector_loop_factory() -> asyncio.AbstractEventLoop:
    return asyncio.SelectorEventLoop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the RAG HTTP/MCP server.")
    parser.add_argument(
        "expose", nargs="?", default="expose=false",
        choices=("expose=true", "expose=false"),
        help="Listen on all network interfaces when expose=true (default: expose=false).",
    )
    args = parser.parse_args()
    uvicorn.run(
        "rag.main:app",
        host="0.0.0.0" if args.expose == "expose=true" else "127.0.0.1",
        port=8123,
        reload=False,
        loop="rag.main:selector_loop_factory",
    )


if __name__ == "__main__":
    main()
