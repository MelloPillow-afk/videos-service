"""Processed media appears on videos; viewers play published, ready videos, and admins
preview ready videos before publishing."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from psycopg import AsyncConnection

from tests.utilities.media_urls import expected_sizes
from tests.utilities.rows import insert_video

pytestmark = pytest.mark.integration

PLAYBACK_KEY = "videos/v/uploads/u/hls/master.m3u8"
THUMBNAIL_PREFIX = "videos/v/uploads/u/thumbnails"


async def insert_processed_video(db: AsyncConnection, **values: object) -> str:
    video_id = await insert_video(
        db,
        status="READY",
        size_bytes=1024,
        duration_seconds=12.5,
        playback_key=PLAYBACK_KEY,
        generated_thumbnail_prefix=THUMBNAIL_PREFIX,
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
        "url": f"https://media.example.com/{THUMBNAIL_PREFIX}/xl.jpg",
        "sizes": expected_sizes(THUMBNAIL_PREFIX),
    }


async def test_processed_media_appears_in_the_catalog(
    client: AsyncClient, db: AsyncConnection
) -> None:
    await insert_processed_video(
        db, publication_status="PUBLISHED", published_at="2026-10-13T14:00:00Z"
    )

    (video,) = (await client.get("/v1/videos")).json()["data"]

    assert video["duration_seconds"] == 12.5
    assert video["thumbnail"]["sizes"] == expected_sizes(THUMBNAIL_PREFIX)


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


async def test_admin_previews_a_ready_draft(client: AsyncClient, db: AsyncConnection) -> None:
    video_id = await insert_processed_video(db)

    response = await client.get(f"/v1/admin/videos/{video_id}/playback")

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "playback": {"type": "hls", "url": f"https://media.example.com/{PLAYBACK_KEY}"},
    }


async def test_admin_preview_of_an_unprocessed_video_is_not_ready(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(db, status="PROCESSING")

    response = await client.get(f"/v1/admin/videos/{video_id}/playback")

    assert response.status_code == 409
    assert response.json() == {"detail": "The video is not ready."}


async def test_admin_cannot_preview_a_deleted_video(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_processed_video(db, deleted_at="2026-10-14T09:00:00Z")

    response = await client.get(f"/v1/admin/videos/{video_id}/playback")

    assert response.status_code == 404
    assert response.json() == {"detail": "The video was not found."}


async def test_admin_cannot_preview_a_missing_video(client: AsyncClient) -> None:
    response = await client.get(f"/v1/admin/videos/{uuid4()}/playback")

    assert response.status_code == 404


async def test_admin_preview_requires_a_token(client: AsyncClient, db: AsyncConnection) -> None:
    video_id = await insert_processed_video(db)
    del client.headers["Authorization"]

    response = await client.get(f"/v1/admin/videos/{video_id}/playback")

    assert response.status_code == 401
