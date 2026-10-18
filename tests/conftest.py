"""Each integration test owns a temporary schema in a dedicated test database."""

from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any, LiteralString, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from psycopg import AsyncConnection, sql
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.app import create_app
from src.clients import cloudflare, gcp, local
from src.clients.cloudflare import PresignedUpload
from src.config import Settings
from src.services import thumbnails as thumbnails_service
from src.services import uploads as uploads_service
from tests.generated._support import APICase
from tests.utilities.auth_provider import AUTH_SETTINGS, LocalSigningKeys
from tests.utilities.fakes import FakeLauncher, FakeStorage
from tests.utilities.media_urls import MEDIA_BASE_URL, expected_sizes
from tests.utilities.rows import insert_video

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


@pytest.fixture(autouse=True)
def storage(monkeypatch: pytest.MonkeyPatch) -> FakeStorage:
    """Every test uses in-memory storage in place of R2."""
    fake = FakeStorage()
    monkeypatch.setattr(cloudflare, "presign_upload", fake.presign_upload)
    monkeypatch.setattr(cloudflare, "uploaded_size", fake.uploaded_size)
    monkeypatch.setattr(cloudflare, "download_source", fake.download_source)
    monkeypatch.setattr(cloudflare, "upload_media", fake.upload_media)
    return fake


@pytest.fixture(autouse=True)
def launcher(monkeypatch: pytest.MonkeyPatch) -> FakeLauncher:
    """Every test records worker launches instead of starting workers."""
    fake = FakeLauncher()
    monkeypatch.setattr(local, "run_job", fake.run_job)
    monkeypatch.setattr(gcp, "run_job", fake.run_job)
    return fake


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
        Settings(
            database_url=SecretStr(url),
            db_schema=schema,
            media_base_url=MEDIA_BASE_URL,
            **AUTH_SETTINGS,
        ),
        signing_keys=signing_keys,
    )


@pytest_asyncio.fixture
async def arrange_jobs_get_job(api_case: APICase, db: AsyncConnection) -> None:
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


@pytest_asyncio.fixture
async def arrange_admin_videos_list_videos(api_case: APICase, db: AsyncConnection) -> None:
    (video,) = api_case.expected_body["data"]
    await insert_video(
        db,
        **{
            column: video[column]
            for column in ("id", "title", "description", "status", "publication_status")
        },
        created_at=video["created_at"],
        updated_at=video["updated_at"],
    )


@pytest_asyncio.fixture
async def arrange_videos_list_videos(api_case: APICase, db: AsyncConnection) -> None:
    (video,) = api_case.expected_body["data"]
    await insert_video(
        db,
        id=video["id"],
        title=video["title"],
        description=video["description"],
        status="READY",
        publication_status="PUBLISHED",
        published_at=video["published_at"],
        custom_thumbnail_prefix=thumbnail_prefix(video["thumbnail"]),
    )
    # Processing, which sets the duration, is outside this operation.
    video["duration_seconds"] = None


@pytest_asyncio.fixture
async def arrange_admin_videos_upload_url(
    api_case: APICase, db: AsyncConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    await insert_video(db, id=api_case.path_params["id"])
    # The example's file is larger than the default size limit.
    api_case.body["size_bytes"] = 1024
    upload = api_case.expected_body["upload"]
    monkeypatch.setattr(uploads_service, "uuid4", lambda: UUID(upload["upload_id"]))
    example = PresignedUpload(
        url=upload["url"], expires_at=datetime.fromisoformat(upload["expires_at"])
    )

    def presign_upload(_key: str, _content_type: str) -> PresignedUpload:
        return example

    monkeypatch.setattr(cloudflare, "presign_upload", presign_upload)


@pytest_asyncio.fixture
async def arrange_admin_thumbnails_upload_url(
    api_case: APICase, db: AsyncConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    await insert_video(db, id=api_case.path_params["id"])
    upload = api_case.expected_body["upload"]
    monkeypatch.setattr(thumbnails_service, "uuid4", lambda: UUID(upload["upload_id"]))
    example = PresignedUpload(
        url=upload["url"], expires_at=datetime.fromisoformat(upload["expires_at"])
    )

    def presign_upload(_key: str, _content_type: str) -> PresignedUpload:
        return example

    monkeypatch.setattr(cloudflare, "presign_upload", presign_upload)


@pytest_asyncio.fixture
async def arrange_admin_thumbnails_delete_thumbnail(api_case: APICase, db: AsyncConnection) -> None:
    # The example's custom thumbnail is removed, revealing the generated one.
    generated_prefix = f"videos/{api_case.path_params['id']}/uploads/{uuid4()}/thumbnails"
    await insert_video(
        db,
        id=api_case.path_params["id"],
        generated_thumbnail_prefix=generated_prefix,
        custom_thumbnail_prefix=thumbnail_prefix(api_case.expected_body["thumbnail"]),
    )
    await db.execute(
        "INSERT INTO jobs (video_id, kind, status) VALUES (%s, 'THUMBNAIL_GENERATION', 'SUCCEEDED')",
        (api_case.path_params["id"],),
    )
    api_case.expected_body["thumbnail"] |= {
        "source": "GENERATED",
        "url": f"{MEDIA_BASE_URL}/{generated_prefix}/xl.jpg",
        "sizes": expected_sizes(generated_prefix),
    }


def thumbnail_prefix(thumbnail: dict[str, Any]) -> str:
    """The stored prefix of an example thumbnail's sizes."""
    url: str = thumbnail["url"]
    return url.removeprefix(f"{MEDIA_BASE_URL}/").removesuffix("/xl.jpg")


@pytest_asyncio.fixture
async def arrange_playback_get_playback(api_case: APICase, db: AsyncConnection) -> None:
    playback_url: str = api_case.expected_body["playback"]["url"]
    await insert_video(
        db,
        id=api_case.path_params["id"],
        status="READY",
        publication_status="PUBLISHED",
        published_at="2026-10-13T14:00:00Z",
        playback_key=playback_url.removeprefix(f"{MEDIA_BASE_URL}/"),
    )
