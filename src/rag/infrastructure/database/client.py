from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def sqlalchemy_url(dsn: str) -> str:
    if dsn.startswith("postgresql+psycopg://"):
        return dsn
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    if dsn.startswith("postgres://"):
        return dsn.replace("postgres://", "postgresql+psycopg://", 1)
    return dsn


class Database:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

    async def connect(self) -> None:
        if self.engine is None:
            engine = create_async_engine(
                sqlalchemy_url(self._dsn), pool_size=10, max_overflow=0,
            )
            try:
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT TRUE"))
            except Exception:
                await engine.dispose()
                raise
            self.engine = engine
            self.session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def close(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

    def require_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self.session_factory is None:
            raise RuntimeError("database is not connected")
        return self.session_factory

    async def ping(self) -> bool:
        async with self.require_session_factory()() as session:
            return bool(await session.scalar(text("SELECT TRUE")))
