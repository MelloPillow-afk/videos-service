"""Independent thumbnail outcomes through HTTP with PostgreSQL and real FFmpeg."""

import subprocess
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection, sql

from src.config import Settings
from src.worker import run_job
from tests.providers import LocalSigningKeys
from tests.storage_provider import MemoryStorage

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def thumbnail_client(
    api_app: FastAPI, signing_keys: LocalSigningKeys
) -> AsyncIterator[AsyncClient]:
    async with (
        api_app.router.lifespan_context(api_app),
        AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
            headers={"Authorization": "Bearer " + signing_keys.token()},
        ) as client,
    ):
        yield client


def source_video(path: Path, *, size: str = "180x320") -> bytes:
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=lime:s={size}:r=5:d=1",
            "-c:v",
            "libx264",
            "-threads",
            "2",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path.read_bytes()


async def seed_thumbnail(
    client: AsyncClient,
    test_database: tuple[str, str],
    storage: MemoryStorage,
    source: bytes,
    *,
    status: str = "PROCESSING",
) -> tuple[str, UUID]:
    draft = await client.post("/v1/videos", json={"title": "Independent thumbnail"})
    assert draft.status_code == 201
    video_id, job_id = draft.json()["id"], uuid4()
    source_key = f"videos/{video_id}/source.mp4"
    storage.objects[("private", source_key)] = source, "video/mp4"
    url, schema = test_database
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        await connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        await connection.execute(
            "UPDATE videos SET status=%s,source_key=%s,size_bytes=%s WHERE id=%s",
            (status, source_key, len(source), video_id),
        )
        await connection.execute(
            """INSERT INTO jobs(id,video_id,kind,output_prefix,created_at,updated_at)
            VALUES (%s,%s,'THUMBNAIL',%s,%s,%s)""",
            (
                job_id,
                video_id,
                f"videos/{video_id}/jobs/{job_id}/",
                datetime.now(UTC),
                datetime.now(UTC),
            ),
        )
    return draft.headers["Location"], job_id


async def test_generated_thumbnail_finishes_without_changing_video_processing(
    thumbnail_client: AsyncClient,
    api_app: FastAPI,
    storage: MemoryStorage,
    test_database: tuple[str, str],
    tmp_path: Path,
) -> None:
    path, job = await seed_thumbnail(
        thumbnail_client, test_database, storage, source_video(tmp_path / "portrait.mp4")
    )
    await run_job(job, api_app.state.database, storage, Settings())
    video = (await thumbnail_client.get(path)).json()
    assert video["status"] == "PROCESSING"
    assert video["publication_status"] == "DRAFT"
    assert video["thumbnail"]["status"] == "READY"
    assert video["thumbnail"]["source"] == "GENERATED"
