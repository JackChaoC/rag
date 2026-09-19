from __future__ import annotations

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


class Database:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self.pool: AsyncConnectionPool | None = None

    async def connect(self) -> None:
        if self.pool is None:
            self.pool = AsyncConnectionPool(
                self._dsn, min_size=1, max_size=10, open=False,
                kwargs={"row_factory": dict_row},
            )
            await self.pool.open(wait=True)

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    def require_pool(self) -> AsyncConnectionPool:
        if self.pool is None:
            raise RuntimeError("database is not connected")
        return self.pool

    async def ping(self) -> bool:
        async with self.require_pool().connection() as connection:
            cursor = await connection.execute("SELECT TRUE AS ok")
            row = await cursor.fetchone()
            return bool(row and row["ok"])
