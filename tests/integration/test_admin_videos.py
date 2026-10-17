"""Admins manage videos stored in PostgreSQL through the real application."""

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from psycopg import AsyncConnection

from tests.rows import insert_video

pytestmark = pytest.mark.integration


async def test_created_video_is_a_stored_draft(client: AsyncClient, db: AsyncConnection) -> None:
    response = await client.post(
        "/v1/admin/videos",
        json={"title": "Introduction to Faith", "description": "An introductory lesson"},
    )

    assert response.status_code == 201
    video = response.json()
    assert response.headers["Location"] == f"/v1/admin/videos/{video['id']}"
    assert video | {"id": None, "created_at": None, "updated_at": None} == {
        "id": None,
        "title": "Introduction to Faith",
        "description": "An introductory lesson",
        "status": "CREATED",
        "publication_status": "DRAFT",
        "size_bytes": None,
        "duration_seconds": None,
        "thumbnail": {"status": "PENDING", "source": "NONE", "url": None},
        "published_at": None,
        "created_at": None,
        "updated_at": None,
        "latest_job_id": None,
    }
    assert video["created_at"] == video["updated_at"]
    assert video["created_at"].endswith("Z")
    cursor = await db.execute(
        "SELECT title, description, status, publication_status FROM videos WHERE id = %s",
        (video["id"],),
    )
    assert await cursor.fetchone() == (
        "Introduction to Faith",
        "An introductory lesson",
        "CREATED",
        "DRAFT",
    )


async def test_description_is_optional(client: AsyncClient) -> None:
    response = await client.post("/v1/admin/videos", json={"title": "Introduction to Faith"})

    assert response.status_code == 201
    assert response.json()["description"] is None


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 201},
        {"title": None},
        {"title": "Introduction to Faith", "description": "x" * 5001},
    ],
)
async def test_invalid_videos_are_rejected(
    client: AsyncClient, db: AsyncConnection, body: dict[str, Any]
) -> None:
    response = await client.post("/v1/admin/videos", json=body)

    assert response.status_code == 422
    cursor = await db.execute("SELECT count(*) FROM videos")
    assert await cursor.fetchone() == (0,)


async def test_created_video_can_be_read_back(client: AsyncClient) -> None:
    created = (
        await client.post("/v1/admin/videos", json={"title": "Introduction to Faith"})
    ).json()

    response = await client.get(f"/v1/admin/videos/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


async def test_video_reports_its_processing_job(client: AsyncClient, db: AsyncConnection) -> None:
    video_id = await insert_video(db, status="PROCESSING")
    cursor = await db.execute(
        "INSERT INTO jobs (video_id, kind) VALUES (%s, 'VIDEO_PROCESSING'), "
        "(%s, 'THUMBNAIL_GENERATION') RETURNING id, kind",
        (video_id, video_id),
    )
    jobs = {kind: str(job_id) for job_id, kind in await cursor.fetchall()}

    response = await client.get(f"/v1/admin/videos/{video_id}")

    assert response.status_code == 200
    assert response.json()["latest_job_id"] == jobs["VIDEO_PROCESSING"]


async def test_published_video_reports_when(client: AsyncClient, db: AsyncConnection) -> None:
    video_id = await insert_video(
        db,
        status="READY",
        publication_status="PUBLISHED",
        published_at="2026-10-13T15:00:00+00:00",
    )

    response = await client.get(f"/v1/admin/videos/{video_id}")

    assert response.json()["published_at"] == "2026-10-13T15:00:00Z"


@pytest.mark.parametrize("deleted", [False, True], ids=["missing", "deleted"])
async def test_missing_or_deleted_video_is_not_found(
    client: AsyncClient, db: AsyncConnection, deleted: bool
) -> None:
    video_id = await insert_video(db, deleted_at="2026-10-14T09:00:00Z") if deleted else uuid4()

    response = await client.get(f"/v1/admin/videos/{video_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "The video was not found."}
