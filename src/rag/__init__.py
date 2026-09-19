"""Local RAG indexing and retrieval service."""

import asyncio
import sys


if sys.platform == "win32":
    # Psycopg's async implementation requires a selector-based loop on Windows.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
