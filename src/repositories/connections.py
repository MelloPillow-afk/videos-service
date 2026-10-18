"""Process-wide database pool that repositories borrow connections from."""

from contextlib import AbstractAsyncContextManager

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from src.config import Settings
from src.repositories.database import Database

_database: Database | None = None


async def open_database(settings: Settings) -> None:
    """Open the process-wide pool; the application lifespan calls this on startup."""
    global _database
    _database = Database(settings)
    await _database.connect()


async def close_database() -> None:
    global _database
    if _database is not None:
        await _database.close()
        _database = None


def db_connection() -> AbstractAsyncContextManager[AsyncConnection[TupleRow]]:
    """Borrow a pooled connection: commit on success, roll back on failure."""
    if _database is None:
        raise RuntimeError("The database is not open; it opens in the application lifespan")
    return _database.connection()
