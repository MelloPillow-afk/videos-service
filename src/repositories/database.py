"""Small asynchronous PostgreSQL pool owned by the persistence layer."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg_pool import AsyncConnectionPool

from src.config import Settings


class Database:
    def __init__(self, settings: Settings) -> None:
        self._schema = settings.db_schema
        self._statement_timeout_ms = settings.db_statement_timeout_ms
        self._pool = AsyncConnectionPool[AsyncConnection[TupleRow]](
            conninfo=settings.database_url.get_secret_value(),
            open=False,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            timeout=settings.db_pool_timeout_seconds,
            kwargs={
                "connect_timeout": settings.db_connect_timeout_seconds,
            },
        )

    async def connect(self) -> None:
        await self._pool.open(wait=False)

    async def close(self) -> None:
        await self._pool.close()

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[AsyncConnection[TupleRow]]:
        """Apply transaction-local policy, then commit or roll back the caller's work."""
        async with self._pool.connection() as connection:
            # Neon transaction pooling rejects startup options and cannot retain
            # session settings. The first statement starts this same transaction;
            # local settings expire on commit/rollback before a backend is reused.
            await connection.execute(
                "SELECT set_config('statement_timeout',%s,true),"
                "set_config('lock_timeout',%s,true),set_config('search_path',%s,true)",
                (str(self._statement_timeout_ms), str(self._statement_timeout_ms), self._schema),
            )
            yield connection
