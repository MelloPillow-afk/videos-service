"""HTTP timestamps are UTC even when PostgreSQL returns a different session offset."""

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.app import create_app
from src.config import Settings
from src.repositories.database import Database
from tests.job_provider import RecordingLauncher
from tests.providers import LocalSigningKeys
from tests.storage_provider import MemoryStorage

pytestmark = pytest.mark.integration


async def test_video_and_upload_timestamps_are_utc_in_non_utc_database_session(
    api_app: FastAPI,
    signing_keys: LocalSigningKeys,
    storage: MemoryStorage,
    launcher: RecordingLauncher,
) -> None:
    settings: Settings = api_app.state.settings.model_copy(
        update={"db_pool_min_size": 1, "db_pool_max_size": 1}
    )
    now = datetime(2026, 10, 16, 15, tzinfo=UTC)
    app = create_app(
        settings, signing_keys=signing_keys, storage=storage, launcher=launcher, clock=lambda: now
    )
    database: Database = app.state.database
    async with app.router.lifespan_context(app):
        async with database.connection() as connection:
            await connection.execute("SET TIME ZONE 'America/Chicago'")
            assert await (await connection.execute("SHOW timezone")).fetchone() == (
                "America/Chicago",
            )
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": "Bearer " + signing_keys.token()},
        ) as client:
            created = await client.post("/v1/videos", json={"title": "UTC wire"})
            assert created.status_code == 201
            assert (
                created.json()["created_at"]
                == created.json()["updated_at"]
                == "2026-10-16T15:00:00Z"
            )
            path = created.headers["Location"]
            source = await client.post(
                path + ":upload-url",
                json={
                    "file_name": "source.mp4",
                    "content_type": "video/mp4",
                    "size_bytes": 12,
                },
            )
            assert source.status_code == 200
            assert source.json()["upload"]["expires_at"] == "2026-10-16T15:15:00Z"
            image = await client.post(
                path + "/thumbnails:upload-url",
                json={
                    "file_name": "cover.jpg",
                    "content_type": "image/jpeg",
                    "size_bytes": 12,
                },
            )
            assert image.status_code == 200
            assert image.json()["upload"]["expires_at"] == "2026-10-16T15:15:00Z"
            async with database.connection() as connection:
                await connection.execute(
                    "UPDATE videos SET status='READY' WHERE id=%s", (created.json()["id"],)
                )
            published = await client.patch(path, json={"publication_status": "PUBLISHED"})
            assert published.status_code == 200
            assert published.json()["published_at"] == "2026-10-16T15:00:00Z"
            assert (await client.get(path)).json() == published.json()
            page = await client.get("/v1/videos")
            assert page.json()["data"] == [published.json()]
