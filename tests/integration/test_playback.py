"""Processed media appears on videos, and viewers play published, ready videos."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from psycopg import AsyncConnection

from tests.rows import insert_video

pytestmark = pytest.mark.integration

PLAYBACK_KEY = "videos/v/uploads/u/hls/master.m3u8"
THUMBNAIL_KEY = "videos/v/uploads/u/thumbnail.jpg"


async def insert_processed_video(db: AsyncConnection, **values: object) -> str:
    video_id = await insert_video(
        db,
        status="READY",
        size_bytes=1024,
        duration_seconds=12.5,
        playback_key=PLAYBACK_KEY,
        generated_thumbnail_key=THUMBNAIL_KEY,
        **values,
    )
    await db.execute(
        "INSERT INTO jobs (video_id, kind, status) VALUES "
        "(%(id)s, 'VIDEO_PROCESSING', 'SUCCEEDED'), (%(id)s, 'THUMBNAIL_GENERATION', 'SUCCEEDED')",
        {"id": video_id},
    )
    return video_id


async def test_processed_media_appears_on_the_admin_video(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_processed_video(db)

    video = (await client.get(f"/v1/admin/videos/{video_id}")).json()

    assert (video["size_bytes"], video["duration_seconds"]) == (1024, 12.5)
    assert video["thumbnail"] == {
        "status": "READY",
        "source": "GENERATED",
        "url": f"https://media.example.com/{THUMBNAIL_KEY}",
    }


async def test_processed_media_appears_in_the_catalog(
    client: AsyncClient, db: AsyncConnection
) -> None:
    await insert_processed_video(
        db, publication_status="PUBLISHED", published_at="2026-10-13T14:00:00Z"
    )

    (video,) = (await client.get("/v1/videos")).json()["data"]

    assert video["duration_seconds"] == 12.5
    assert video["thumbnail"]["url"] == f"https://media.example.com/{THUMBNAIL_KEY}"


async def test_published_ready_video_plays(client: AsyncClient, db: AsyncConnection) -> None:
    video_id = await insert_processed_video(
        db, publication_status="PUBLISHED", published_at="2026-10-13T14:00:00Z"
    )

    response = await client.get(f"/v1/videos/{video_id}/playback")

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "playback": {"type": "hls", "url": f"https://media.example.com/{PLAYBACK_KEY}"},
    }


async def test_draft_video_does_not_play(client: AsyncClient, db: AsyncConnection) -> None:
    video_id = await insert_processed_video(db)

    response = await client.get(f"/v1/videos/{video_id}/playback")

    assert response.status_code == 404


async def test_missing_video_does_not_play(client: AsyncClient) -> None:
    response = await client.get(f"/v1/videos/{uuid4()}/playback")

    assert response.status_code == 404


async def test_published_video_without_media_is_not_ready(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(
        db, status="PROCESSING", publication_status="PUBLISHED", published_at="2026-10-13T14:00:00Z"
    )

    response = await client.get(f"/v1/videos/{video_id}/playback")

    assert response.status_code == 409
    assert response.json() == {"detail": "The video is not ready."}
