"""Exercise real pooled PostgreSQL transactions and query timeouts."""

import pytest
from psycopg import errors, sql
from pydantic import SecretStr

from src.config import Settings
from src.repositories import Database

pytestmark = pytest.mark.integration


async def test_pool_commits_and_rolls_back(test_database: tuple[str, str]) -> None:
    url, schema = test_database
    table = sql.Identifier(schema, "probe")
    database = Database(Settings(database_url=SecretStr(url), db_pool_max_size=1))
    await database.connect()
    try:
        async with database.connection() as connection:
            await connection.execute(
                sql.SQL("CREATE TABLE {} (id integer PRIMARY KEY)").format(table)
            )
            await connection.execute(sql.SQL("INSERT INTO {} VALUES (1)").format(table))
        with pytest.raises(RuntimeError, match="rollback probe"):
            async with database.connection() as connection:
                await connection.execute(sql.SQL("INSERT INTO {} VALUES (2)").format(table))
                raise RuntimeError("rollback probe")
        async with database.connection() as connection:
            cursor = await connection.execute(
                sql.SQL("SELECT id FROM {} ORDER BY id").format(table)
            )
            assert await cursor.fetchall() == [(1,)]
    finally:
        await database.close()


async def test_queries_have_a_bounded_timeout(test_database: tuple[str, str]) -> None:
    url, _ = test_database
    database = Database(Settings(database_url=SecretStr(url), db_statement_timeout_ms=50))
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
