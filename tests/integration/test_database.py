"""Exercise real pooled PostgreSQL transactions and query timeouts."""

import pytest
from psycopg import AsyncConnection, errors, sql
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


async def test_pool_uses_the_configured_isolated_schema(test_database: tuple[str, str]) -> None:
    url, schema = test_database
    database = Database(Settings(database_url=SecretStr(url), db_schema=schema))
    await database.connect()
    try:
        async with database.connection() as connection:
            cursor = await connection.execute("SELECT current_schema()")
            assert await cursor.fetchone() == (schema,)
            await connection.execute("CREATE TABLE isolated_probe (id integer)")
            cursor = await connection.execute(
                "SELECT table_schema FROM information_schema.tables WHERE table_name = 'isolated_probe'"
            )
            assert await cursor.fetchall() == [(schema,)]
    finally:
        await database.close()


async def test_pool_applies_schema_and_timeouts_per_transaction_without_session_leaks(
    test_database: tuple[str, str],
) -> None:
    url, schema = test_database
    database = Database(
        Settings(
            database_url=SecretStr(url),
            db_schema=schema,
            db_pool_min_size=1,
            db_pool_max_size=1,
            db_statement_timeout_ms=50,
        )
    )
    await database.connect()
    try:
        async with database.connection() as connection:
            cursor = await connection.execute(
                "SELECT current_schema(),current_setting('statement_timeout'),"
                "current_setting('lock_timeout'),pg_backend_pid()"
            )
            first = await cursor.fetchone()
            assert first is not None and first[:3] == (schema, "50ms", "50ms")
            # Session defaults must remain untouched for transaction-mode poolers.
            cursor = await connection.execute(
                "SELECT reset_val FROM pg_settings WHERE name='search_path'"
            )
            assert await cursor.fetchone() != (schema,)
            await connection.execute(
                "SELECT set_config('search_path','public',true),"
                "set_config('statement_timeout','0',true),set_config('lock_timeout','0',true)"
            )
        # A committed caller-local override must not affect the next borrower.
        async with database.connection() as connection:
            cursor = await connection.execute(
                "SELECT current_schema(),current_setting('statement_timeout'),"
                "current_setting('lock_timeout'),pg_backend_pid()"
            )
            assert await cursor.fetchone() == first
        with pytest.raises(errors.QueryCanceled):
            async with database.connection() as connection:
                await connection.execute(
                    "SELECT set_config('search_path','public',true),"
                    "set_config('lock_timeout','0',true)"
                )
                await connection.execute("SELECT pg_sleep(1)")
        # An aborted transaction also releases its local configuration.
        async with database.connection() as connection:
            cursor = await connection.execute(
                "SELECT current_schema(),current_setting('statement_timeout'),"
                "current_setting('lock_timeout'),pg_backend_pid()"
            )
            assert await cursor.fetchone() == first
    finally:
        await database.close()


async def test_lock_wait_is_bounded_and_pool_recovers(test_database: tuple[str, str]) -> None:
    url, schema = test_database
    database = Database(
        Settings(
            database_url=SecretStr(url),
            db_schema=schema,
            db_pool_min_size=1,
            db_pool_max_size=1,
            db_statement_timeout_ms=50,
        )
    )
    await database.connect()
    try:
        async with database.connection() as connection:
            await connection.execute("CREATE TABLE lock_probe (id integer PRIMARY KEY)")
            await connection.execute("INSERT INTO lock_probe VALUES (1)")
        async with await AsyncConnection.connect(url) as blocker:
            await blocker.execute(
                sql.SQL("LOCK TABLE {}.lock_probe IN ACCESS EXCLUSIVE MODE").format(
                    sql.Identifier(schema)
                )
            )
            with pytest.raises(errors.LockNotAvailable):
                async with database.connection() as connection:
                    # Distinguish lock_timeout from the equal statement timeout.
                    await connection.execute("SET LOCAL statement_timeout='1s'")
                    await connection.execute("SELECT id FROM lock_probe")
        async with database.connection() as connection:
            cursor = await connection.execute("SELECT id FROM lock_probe")
            assert await cursor.fetchall() == [(1,)]
    finally:
        await database.close()
