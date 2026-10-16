"""Each integration test owns a temporary schema in a dedicated test database."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import LiteralString, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from psycopg import AsyncConnection, sql
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.app import create_app
from src.config import Settings
from tests.generated._support import APICase
from tests.providers import ISSUER, SUBJECT, LocalSigningKeys


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
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema + "_auth"))
            )
            await connection.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )


@pytest_asyncio.fixture
async def api_app(
    test_database: tuple[str, str], signing_keys: LocalSigningKeys, request: pytest.FixtureRequest
) -> FastAPI:
    """Generated HTTP tests use the real app and a fresh PostgreSQL schema."""
    url, schema = test_database
    await apply_app_migrations(url, schema)
    await arrange_auth_directory(url, schema)
    if request.node.get_closest_marker("api_case"):  # pyright: ignore[reportUnknownMemberType]
        return create_app(
            Settings(
                database_url=SecretStr(url),
                db_schema=schema,
                auth_schema=schema + "_auth",
                auth_issuer=ISSUER,
                auth_audience=ISSUER,
            ),
            signing_keys=signing_keys,
            clock=lambda: datetime(2026, 10, 13, 14, tzinfo=UTC),
            new_id=lambda: UUID("550e8400-e29b-41d4-a716-446655440000"),
        )
    return create_app(
        Settings(
            database_url=SecretStr(url),
            db_schema=schema,
            auth_schema=schema + "_auth",
            auth_issuer=ISSUER,
            auth_audience=ISSUER,
        ),
        signing_keys=signing_keys,
    )


async def apply_app_migrations(url: str, schema: str) -> None:
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        for migration in sorted((Path(__file__).parents[1] / "migrations").glob("*.sql")):
            if not migration.name.endswith(".rollback.sql"):
                # These trusted checked-in files are executable migration SQL.
                await connection.execute(sql.SQL(cast(LiteralString, migration.read_text())))


@pytest.fixture
def signing_keys() -> LocalSigningKeys:
    return LocalSigningKeys()


async def arrange_auth_directory(url: str, schema: str) -> None:
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema + "_auth"))
        )
        await connection.execute(
            sql.SQL('CREATE TABLE {}."user" (id text PRIMARY KEY, role text)').format(
                sql.Identifier(schema + "_auth")
            )
        )
        await connection.execute(
            sql.SQL('INSERT INTO {}."user" VALUES (%s, %s)').format(
                sql.Identifier(schema + "_auth")
            ),
            (SUBJECT, "admin"),
        )


@pytest.fixture
def arrange_videos_create_video(api_case: APICase, signing_keys: LocalSigningKeys) -> None:
    api_case.headers["Authorization"] = "Bearer " + signing_keys.token()


@pytest_asyncio.fixture
async def arrange_videos_get_video(
    api_case: APICase, api_client: AsyncClient, signing_keys: LocalSigningKeys
) -> None:
    api_case.headers["Authorization"] = "Bearer " + signing_keys.token()
    response = await api_client.post(
        "/v1/videos",
        headers=api_case.headers,
        json={"title": "Introduction to Faith", "description": "An introductory lesson"},
    )
    assert response.status_code == 201


@pytest_asyncio.fixture
async def arrange_videos_update_video(
    api_case: APICase, api_client: AsyncClient, signing_keys: LocalSigningKeys
) -> None:
    api_case.headers["Authorization"] = "Bearer " + signing_keys.token()
    response = await api_client.post(
        "/v1/videos",
        headers=api_case.headers,
        json={"title": "Introduction to Faith", "description": "An introductory lesson"},
    )
    assert response.status_code == 201
