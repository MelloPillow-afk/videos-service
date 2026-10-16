"""Each integration test owns a temporary schema in a dedicated test database."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import LiteralString, cast
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from PIL import Image
from psycopg import AsyncConnection, sql
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.app import create_app
from src.config import Settings
from tests.generated._support import APICase
from tests.providers import ISSUER, SUBJECT, LocalSigningKeys
from tests.storage_provider import MemoryStorage


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
    test_database: tuple[str, str],
    signing_keys: LocalSigningKeys,
    request: pytest.FixtureRequest,
    storage: MemoryStorage,
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
            storage=storage,
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
        storage=storage,
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


async def arrange_ready_example(test_database: tuple[str, str]) -> None:
    """Seed a completed peer state; real processing has its own acceptance seam."""
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        await connection.execute(
            """INSERT INTO videos
            (id,title,description,status,publication_status,size_bytes,duration_seconds,
             playback_key,custom_thumbnail_key,published_at,created_at,updated_at)
            VALUES (%s,%s,%s,'READY','PUBLISHED',52428800,147.5,%s,%s,
                    '2026-10-13T15:00:00Z','2026-10-13T14:00:00Z','2026-10-13T15:00:00Z')""",
            (
                UUID("550e8400-e29b-41d4-a716-446655440000"),
                "Introduction to Faith",
                "An introductory lesson",
                "videos/intro/hls/master.m3u8",
                "videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg",
            ),
        )


@pytest_asyncio.fixture
async def arrange_videos_list_videos(
    api_case: APICase,
    test_database: tuple[str, str],
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
) -> None:
    await arrange_ready_example(test_database)
    api_case.headers["Authorization"] = "Bearer " + signing_keys.token()
    # A seeded single-page result has no continuation token. Business pagination
    # cases exercise real returned cursors in test_library.py.
    api_case.query.pop("cursor", None)
    api_case.query.update(status="READY", publication_status="PUBLISHED")
    api_case.expected_body["pagination"] = {"has_more": False, "next_page_token": None}


@pytest_asyncio.fixture
async def arrange_playback_get_playback(
    test_database: tuple[str, str],
    api_app: FastAPI,
) -> None:
    await arrange_ready_example(test_database)


@pytest.fixture
def storage() -> MemoryStorage:
    return MemoryStorage()


@pytest_asyncio.fixture
async def arrange_thumbnails_upload_url(
    api_case: APICase,
    api_client: AsyncClient,
    signing_keys: LocalSigningKeys,
) -> None:
    api_case.headers["Authorization"] = "Bearer " + signing_keys.token()
    created = await api_client.post("/v1/videos", headers=api_case.headers, json={"title": "Cover"})
    assert created.status_code == 201
    id = "550e8400-e29b-41d4-a716-446655440000"
    api_case.expected_body["upload"].update(
        {
            "upload_id": id,
            "url": f"https://uploads.test/videos/{id}/uploads/{id}/thumbnail.jpg?signature=controlled",
            "headers": {"Content-Type": "image/jpeg", "If-None-Match": "*"},
        }
    )


@pytest_asyncio.fixture
async def arrange_thumbnails_complete_upload(
    api_case: APICase,
    api_client: AsyncClient,
    signing_keys: LocalSigningKeys,
    storage: MemoryStorage,
) -> None:
    api_case.headers["Authorization"] = "Bearer " + signing_keys.token()
    created = await api_client.post("/v1/videos", headers=api_case.headers, json={"title": "Cover"})
    assert created.status_code == 201
    output = BytesIO()
    Image.new("RGB", (1280, 720), color="blue").save(output, format="JPEG")
    data = output.getvalue()
    issued = await api_client.post(
        created.headers["Location"] + "/thumbnails:upload-url",
        headers=api_case.headers,
        json={"file_name": "cover.jpg", "content_type": "image/jpeg", "size_bytes": len(data)},
    )
    assert issued.status_code == 200
    upload = issued.json()["upload"]
    await storage.browser_put(upload["url"], data, upload["headers"])
    api_case.body = {"upload_id": upload["upload_id"]}
    id = "550e8400-e29b-41d4-a716-446655440000"
    api_case.expected_body["thumbnail"]["url"] = (
        f"https://media.example.com/videos/{id}/thumbnails/custom/{id}/image.jpg"
    )


@pytest_asyncio.fixture
async def arrange_thumbnails_delete_thumbnail(
    api_case: APICase,
    api_client: AsyncClient,
    signing_keys: LocalSigningKeys,
    test_database: tuple[str, str],
) -> None:
    api_case.headers["Authorization"] = "Bearer " + signing_keys.token()
    created = await api_client.post("/v1/videos", headers=api_case.headers, json={"title": "Cover"})
    assert created.status_code == 201
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(
            sql.SQL(
                "UPDATE {}.videos SET generated_thumbnail_status='READY',generated_thumbnail_key='fallback.jpg',custom_thumbnail_key='custom.jpg'"
            ).format(sql.Identifier(schema))
        )
    api_case.expected_body["thumbnail"] = {
        "status": "READY",
        "source": "GENERATED",
        "url": "https://media.example.com/fallback.jpg",
    }
