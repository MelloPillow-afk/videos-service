"""Small asynchronous PostgreSQL pool owned by the persistence layer."""

from contextlib import AbstractAsyncContextManager

from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg_pool import AsyncConnectionPool

from src.config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self._pool = AsyncConnectionPool[AsyncConnection[TupleRow]](
            conninfo=settings.database_url.get_secret_value(),
            open=False,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            timeout=settings.db_pool_timeout_seconds,
            kwargs={
                "connect_timeout": settings.db_connect_timeout_seconds,
                "options": (
                    f"-c statement_timeout={settings.db_statement_timeout_ms} "
                    f"-c lock_timeout={settings.db_statement_timeout_ms}"
                ),
            },
        )

    async def connect(self) -> None:
        await self._pool.open(wait=False)

    async def close(self) -> None:
        await self._pool.close()

    def connection(self) -> AbstractAsyncContextManager[AsyncConnection[TupleRow]]:
        """Commit on success, roll back on failure, and return the connection to the pool."""
        return self._pool.connection()
