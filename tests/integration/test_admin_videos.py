"""Admins manage videos stored in PostgreSQL through the real application."""

from typing import Any

import pytest
from httpx import AsyncClient
from psycopg import AsyncConnection

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
