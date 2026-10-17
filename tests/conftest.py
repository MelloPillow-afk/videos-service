"""Each integration test owns a temporary schema in a dedicated test database."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import LiteralString, cast
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
from tests.generated._support import APICase
from tests.rows import insert_video

MIGRATIONS = Path(__file__).parent.parent / "migrations"


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
async def migrated_database(test_database: tuple[str, str]) -> tuple[str, str]:
    """Apply the service migrations in order; test_migrations runs them through Yoyo."""
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            if not migration.name.endswith(".rollback.sql"):
                # Trusted repository files, not user input.
                await connection.execute(cast(LiteralString, migration.read_text()))
    return url, schema


@pytest_asyncio.fixture
async def db(migrated_database: tuple[str, str]) -> AsyncIterator[AsyncConnection]:
    """Autocommit connection for arranging and inspecting rows in the test schema."""
    url, schema = migrated_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        yield connection


@pytest.fixture
def signing_keys() -> LocalSigningKeys:
    return LocalSigningKeys()


@pytest.fixture
def api_bearer_token(signing_keys: LocalSigningKeys) -> str:
    return signing_keys.token()


@pytest_asyncio.fixture
async def api_app(migrated_database: tuple[str, str], signing_keys: LocalSigningKeys) -> FastAPI:
    """Generated HTTP tests use the real app, real JWT checks, and a fresh PostgreSQL schema."""
    url, schema = migrated_database
    return create_app(
        Settings(database_url=SecretStr(url), db_schema=schema, **AUTH_SETTINGS),
        signing_keys=signing_keys,
    )


@pytest_asyncio.fixture
async def arrange_admin_jobs_get_job(api_case: APICase, db: AsyncConnection) -> None:
    job = api_case.expected_body
    await insert_video(db, id=job["video_id"])
    await db.execute(
        "INSERT INTO jobs (id, video_id, kind, status, message) "
        "VALUES (%s, %s, 'VIDEO_PROCESSING', %s, %s)",
        (job["id"], job["video_id"], job["status"], job["message"]),
    )


@pytest_asyncio.fixture
async def arrange_admin_videos_create_video(api_case: APICase, db: AsyncConnection) -> None:
    # The new row takes its id and timestamps from column defaults; pin them to the example.
    video = api_case.expected_body
    await db.execute(
        sql.SQL(
            "ALTER TABLE videos ALTER COLUMN id SET DEFAULT {id}, "
            "ALTER COLUMN created_at SET DEFAULT {created_at}, "
            "ALTER COLUMN updated_at SET DEFAULT {updated_at}"
        ).format(
            id=sql.Literal(video["id"]),
            created_at=sql.Literal(video["created_at"]),
            updated_at=sql.Literal(video["updated_at"]),
        )
    )


@pytest_asyncio.fixture
async def arrange_admin_videos_get_video(api_case: APICase, db: AsyncConnection) -> None:
    await insert_example_video(api_case, db)


@pytest_asyncio.fixture
async def arrange_admin_videos_delete_video(api_case: APICase, db: AsyncConnection) -> None:
    await insert_video(db, id=api_case.path_params["id"])


@pytest_asyncio.fixture
async def arrange_admin_videos_update_video(api_case: APICase, db: AsyncConnection) -> None:
    await insert_example_video(api_case, db)
    # The update stamps updated_at with now(); pin it to the example instead.
    await db.execute(
        sql.SQL(
            "CREATE FUNCTION pin_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN NEW.updated_at := {updated_at}; RETURN NEW; END $$; "
            "CREATE TRIGGER pin_updated_at BEFORE UPDATE ON videos "
            "FOR EACH ROW EXECUTE FUNCTION pin_updated_at()"
        ).format(updated_at=sql.Literal(api_case.expected_body["updated_at"]))
    )


async def insert_example_video(api_case: APICase, db: AsyncConnection) -> None:
    video = api_case.expected_body
    await insert_video(
        db,
        **{
            column: video[column]
            for column in ("id", "title", "description", "status", "publication_status")
        },
        created_at=video["created_at"],
        updated_at=video["updated_at"],
    )
