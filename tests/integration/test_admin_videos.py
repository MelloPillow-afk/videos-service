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
        "thumbnail": {"status": "PENDING", "source": "NONE", "url": None, "sizes": None},
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


async def test_edits_change_only_supplied_fields(client: AsyncClient, db: AsyncConnection) -> None:
    video_id = await insert_video(
        db, description="An introductory lesson", updated_at="2026-10-13T14:00:00Z"
    )

    response = await client.patch(f"/v1/admin/videos/{video_id}", json={"title": "Renamed"})

    assert response.status_code == 200
    video = response.json()
    assert (video["title"], video["description"]) == ("Renamed", "An introductory lesson")
    assert video["updated_at"] > "2026-10-13T14:00:00Z"
    assert (await client.get(f"/v1/admin/videos/{video_id}")).json() == video


async def test_null_description_clears_it(client: AsyncClient, db: AsyncConnection) -> None:
    video_id = await insert_video(db, description="An introductory lesson")

    response = await client.patch(f"/v1/admin/videos/{video_id}", json={"description": None})

    assert response.json()["description"] is None


async def test_ready_video_can_be_published_and_unpublished(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(db, status="READY")
    path = f"/v1/admin/videos/{video_id}"

    published = (await client.patch(path, json={"publication_status": "PUBLISHED"})).json()
    republished = (await client.patch(path, json={"publication_status": "PUBLISHED"})).json()
    unpublished = (await client.patch(path, json={"publication_status": "DRAFT"})).json()

    assert published["publication_status"] == "PUBLISHED"
    assert published["published_at"] is not None
    assert republished["published_at"] == published["published_at"]
    assert (unpublished["publication_status"], unpublished["published_at"]) == ("DRAFT", None)


@pytest.mark.parametrize("status", ["CREATED", "UPLOADING", "PROCESSING", "FAILED"])
async def test_only_ready_videos_can_be_published(
    client: AsyncClient, db: AsyncConnection, status: str
) -> None:
    video_id = await insert_video(db, status=status)

    response = await client.patch(
        f"/v1/admin/videos/{video_id}", json={"publication_status": "PUBLISHED"}
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "The video is not ready."}
    cursor = await db.execute("SELECT publication_status FROM videos WHERE id = %s", (video_id,))
    assert await cursor.fetchone() == ("DRAFT",)


@pytest.mark.parametrize("deleted", [False, True], ids=["missing", "deleted"])
async def test_missing_or_deleted_video_cannot_be_edited(
    client: AsyncClient, db: AsyncConnection, deleted: bool
) -> None:
    video_id = await insert_video(db, deleted_at="2026-10-14T09:00:00Z") if deleted else uuid4()

    response = await client.patch(f"/v1/admin/videos/{video_id}", json={"title": "Renamed"})

    assert response.status_code == 404


@pytest.mark.parametrize(
    "body", [{}, {"color": "blue"}, {"title": None}, {"title": " "}, {"publication_status": None}]
)
async def test_invalid_edits_are_rejected(
    client: AsyncClient, db: AsyncConnection, body: dict[str, Any]
) -> None:
    video_id = await insert_video(db)

    response = await client.patch(f"/v1/admin/videos/{video_id}", json=body)

    assert response.status_code == 422


async def test_deleted_video_is_gone_but_kept_for_cleanup(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(db, status="READY")
    await db.execute(
        "INSERT INTO jobs (video_id, kind, status) VALUES (%s, 'VIDEO_PROCESSING', 'SUCCEEDED')",
        (video_id,),
    )
    path = f"/v1/admin/videos/{video_id}"

    response = await client.delete(path)

    assert response.status_code == 204
    assert response.content == b""
    assert (await client.get(path)).status_code == 404
    assert (await client.delete(path)).status_code == 404
    cursor = await db.execute(
        "SELECT deleted_at IS NOT NULL, (SELECT count(*) FROM jobs WHERE video_id = videos.id) "
        "FROM videos WHERE id = %s",
        (video_id,),
    )
    assert await cursor.fetchone() == (True, 1)


async def test_missing_video_cannot_be_deleted(client: AsyncClient) -> None:
    response = await client.delete(f"/v1/admin/videos/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "The video was not found."}
