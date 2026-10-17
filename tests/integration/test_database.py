"""Queries stop at the configured statement timeout, which HTTP cannot cheaply trigger."""

import pytest
from psycopg import errors
from pydantic import SecretStr

from src.config import Settings
from src.repositories import Database

pytestmark = pytest.mark.integration


async def test_queries_have_a_bounded_timeout(test_database: tuple[str, str]) -> None:
    url, _ = test_database
    database = Database(
        Settings(database_url=SecretStr(url), auth_disabled=True, db_statement_timeout_ms=50)
    )
    await database.connect()
    try:
        with pytest.raises(errors.QueryCanceled):
            async with database.connection() as connection:
                await connection.execute("SELECT pg_sleep(1)")
        async with database.connection() as connection:
            cursor = await connection.execute("SELECT 1")
            assert await cursor.fetchone() == (1,)
    finally:
        await database.close()
