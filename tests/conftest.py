"""Each integration test owns a temporary schema in a dedicated test database."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest_asyncio
from fastapi import FastAPI
from psycopg import AsyncConnection, sql
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.app import create_app
from src.config import Settings


class TestDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    test_database_url: SecretStr = SecretStr(
        "postgresql://videos:videos@localhost:5433/videos_test"
    )


@pytest_asyncio.fixture
async def test_database() -> AsyncIterator[tuple[str, str]]:
    url = TestDatabaseSettings().test_database_url.get_secret_value()
    schema = f"test_{uuid4().hex}"
    async with await AsyncConnection.connect(url, autocommit=True, connect_timeout=5) as connection:
        await connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            yield url, schema
        finally:
            await connection.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )


@pytest_asyncio.fixture
async def api_app(test_database: tuple[str, str]) -> FastAPI:
    """Generated HTTP tests use the real app and a fresh PostgreSQL schema."""
    url, schema = test_database
    return create_app(Settings(database_url=SecretStr(url), db_schema=schema))
