"""Each integration test owns a temporary schema in a dedicated test database."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from psycopg import AsyncConnection, sql
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.app import create_app
from src.config import Settings
from tests.auth_provider import AUTH_SETTINGS, LocalSigningKeys


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


@pytest.fixture
def signing_keys() -> LocalSigningKeys:
    return LocalSigningKeys()


@pytest.fixture
def api_bearer_token(signing_keys: LocalSigningKeys) -> str:
    return signing_keys.token()


@pytest_asyncio.fixture
async def api_app(test_database: tuple[str, str], signing_keys: LocalSigningKeys) -> FastAPI:
    """Generated HTTP tests use the real app, real JWT checks, and a fresh PostgreSQL schema."""
    url, schema = test_database
    return create_app(
        Settings(database_url=SecretStr(url), db_schema=schema, **AUTH_SETTINGS),
        signing_keys=signing_keys,
    )
