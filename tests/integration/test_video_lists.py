"""Admins and viewers page through video lists, and viewers open catalog videos, stored in PostgreSQL."""

import base64
import json
from uuid import uuid4

import pytest
from httpx import AsyncClient
from psycopg import AsyncConnection

from tests.utilities.rows import insert_video

pytestmark = pytest.mark.integration

ADMIN_LIST = "/v1/admin/videos"
CATALOG = "/v1/videos"


async def insert_published(db: AsyncConnection, published_at: str, **values: object) -> str:
    values = {"status": "READY"} | values
    return await insert_video(
        db, publication_status="PUBLISHED", published_at=published_at, **values
    )


async def page_through(client: AsyncClient, path: str, **params: str | int) -> list[list[str]]:
    """IDs on each page, following next_page_token until the last page."""
    pages: list[list[str]] = []
    token = None
    while True:
        query = params | ({"page_token": token} if token else {})
        body = (await client.get(path, params=query)).json()
        pages.append([video["id"] for video in body["data"]])
        assert body["pagination"]["has_more"] == (body["pagination"]["next_page_token"] is not None)
        token = body["pagination"]["next_page_token"]
        if token is None:
            return pages


def token(fields: object) -> str:
    return base64.urlsafe_b64encode(json.dumps(fields).encode()).decode().rstrip("=")


INVALID_TOKENS = [
    "not a token",
    base64.urlsafe_b64encode(b"not json").decode(),
    token(["2026-10-13T14:00:00+00:00", "550e8400-e29b-41d4-a716-446655440000"]),
    token({"t": "2026-10-13T14:00:00+00:00"}),
    token({"t": "2026-10-13T14:00:00", "id": "550e8400-e29b-41d4-a716-446655440000"}),
    token({"t": "yesterday", "id": "550e8400-e29b-41d4-a716-446655440000"}),
    token({"t": "2026-10-13T14:00:00+00:00", "id": "not-a-uuid"}),
    token({"t": 1, "id": "550e8400-e29b-41d4-a716-446655440000"}),
]


async def test_admin_list_shows_every_live_video_newest_created_first(
    client: AsyncClient, db: AsyncConnection
) -> None:
    oldest = await insert_video(db, status="FAILED", created_at="2026-10-11T09:00:00Z")
    published = await insert_published(
        db, "2026-10-13T15:00:00Z", created_at="2026-10-12T09:00:00Z"
    )
    await insert_video(db, created_at="2026-10-13T09:00:00Z", deleted_at="2026-10-14T09:00:00Z")
    newest = await insert_video(db, status="PROCESSING", created_at="2026-10-14T09:00:00Z")
    await db.execute("INSERT INTO jobs (video_id, kind) VALUES (%s, 'VIDEO_PROCESSING')", (newest,))

    response = await client.get(ADMIN_LIST)

    assert response.status_code == 200
    body = response.json()
    assert [video["id"] for video in body["data"]] == [newest, published, oldest]
    assert [video["status"] for video in body["data"]] == ["PROCESSING", "READY", "FAILED"]
    assert body["data"][0]["latest_job_id"] is not None
    assert body["pagination"] == {"next_page_token": None, "has_more": False}


async def test_admin_list_filters_by_publication_status(
    client: AsyncClient, db: AsyncConnection
) -> None:
    draft = await insert_video(db, status="READY")
    published = await insert_published(db, "2026-10-13T15:00:00Z")

    drafts = (await client.get(ADMIN_LIST, params={"publication_status": "DRAFT"})).json()
    publications = (await client.get(ADMIN_LIST, params={"publication_status": "PUBLISHED"})).json()

    assert [video["id"] for video in drafts["data"]] == [draft]
    assert [video["id"] for video in publications["data"]] == [published]


async def test_admin_list_pages_without_skipping_or_repeating(
    client: AsyncClient, db: AsyncConnection
) -> None:
    # Two videos share a creation time, so the id has to break the tie.
    created = ["2026-10-14T09:00:00Z", "2026-10-13T09:00:00Z", "2026-10-13T09:00:00Z"]
    created.append("2026-10-13T09:00:00.000001Z")
    for at in created:
        await insert_video(db, created_at=at)
    await insert_published(db, "2026-10-13T15:00:00Z", created_at="2026-10-13T10:00:00Z")
    expected = [
        row[0]
        for row in await (
            await db.execute(
                "SELECT id::text FROM videos WHERE publication_status = 'DRAFT' "
                "ORDER BY created_at DESC, id DESC"
            )
        ).fetchall()
    ]

    pages = await page_through(client, ADMIN_LIST, limit=2, publication_status="DRAFT")

    assert [len(page) for page in pages] == [2, 2]
    assert [video_id for page in pages for video_id in page] == expected


async def test_catalog_shows_only_ready_published_videos_newest_published_first(
    client: AsyncClient, db: AsyncConnection
) -> None:
    earlier = await insert_published(
        db,
        "2026-10-13T15:00:00Z",
        title="Introduction to Faith",
        description="An introductory lesson",
    )
    later = await insert_published(db, "2026-10-14T15:00:00Z", title="Second Lesson")
    await insert_published(db, "2026-10-15T15:00:00Z", deleted_at="2026-10-16T09:00:00Z")
    await insert_video(db, status="READY")
    # A published video that later leaves READY drops out of the catalog.
    await insert_published(db, "2026-10-15T15:00:00Z", status="PROCESSING")
    del client.headers["Authorization"]

    response = await client.get(CATALOG)

    assert response.status_code == 200
    assert response.json() == {
        "data": [
            {
                "id": later,
                "title": "Second Lesson",
                "description": None,
                "duration_seconds": None,
                "thumbnail": {"status": "PENDING", "source": "NONE", "url": None, "sizes": None},
                "published_at": "2026-10-14T15:00:00Z",
            },
            {
                "id": earlier,
                "title": "Introduction to Faith",
                "description": "An introductory lesson",
                "duration_seconds": None,
                "thumbnail": {"status": "PENDING", "source": "NONE", "url": None, "sizes": None},
                "published_at": "2026-10-13T15:00:00Z",
            },
        ],
        "pagination": {"next_page_token": None, "has_more": False},
    }


async def test_catalog_pages_without_skipping_or_repeating(
    client: AsyncClient, db: AsyncConnection
) -> None:
    # Microsecond-apart and identical publication times must each appear exactly once.
    published = [
        "2026-10-14T15:00:00Z",
        "2026-10-13T15:00:00.000001Z",
        "2026-10-13T15:00:00Z",
        "2026-10-13T15:00:00Z",
        "2026-10-12T15:00:00Z",
    ]
    for at in published:
        await insert_published(db, at)
    cursor = await db.execute("SELECT id::text FROM videos ORDER BY published_at DESC, id DESC")
    expected = [row[0] for row in await cursor.fetchall()]

    pages = await page_through(client, CATALOG, limit=2)

    assert [len(page) for page in pages] == [2, 2, 1]
    assert [video_id for page in pages for video_id in page] == expected


async def test_exactly_full_page_reports_no_more(client: AsyncClient, db: AsyncConnection) -> None:
    for at in ["2026-10-14T15:00:00Z", "2026-10-13T15:00:00Z"]:
        await insert_published(db, at)

    body = (await client.get(CATALOG, params={"limit": 2})).json()

    assert len(body["data"]) == 2
    assert body["pagination"] == {"next_page_token": None, "has_more": False}


async def test_viewer_opens_a_catalog_video(client: AsyncClient, db: AsyncConnection) -> None:
    video_id = await insert_published(
        db,
        "2026-10-13T15:00:00Z",
        title="Introduction to Faith",
        description="An introductory lesson",
    )
    del client.headers["Authorization"]

    response = await client.get(f"{CATALOG}/{video_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": video_id,
        "title": "Introduction to Faith",
        "description": "An introductory lesson",
        "duration_seconds": None,
        "thumbnail": {"status": "PENDING", "source": "NONE", "url": None, "sizes": None},
        "published_at": "2026-10-13T15:00:00Z",
    }


@pytest.mark.parametrize(
    "values",
    [
        {"status": "READY"},
        {
            "status": "PROCESSING",
            "publication_status": "PUBLISHED",
            "published_at": "2026-10-13T15:00:00Z",
        },
        {
            "status": "READY",
            "publication_status": "PUBLISHED",
            "published_at": "2026-10-13T15:00:00Z",
            "deleted_at": "2026-10-14T09:00:00Z",
        },
    ],
    ids=["draft", "not ready", "deleted"],
)
async def test_videos_outside_the_catalog_are_not_found(
    client: AsyncClient, db: AsyncConnection, values: dict[str, str]
) -> None:
    video_id = await insert_video(db, **values)

    response = await client.get(f"{CATALOG}/{video_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "The video was not found."}


async def test_missing_catalog_video_is_not_found(client: AsyncClient) -> None:
    response = await client.get(f"{CATALOG}/{uuid4()}")

    assert response.status_code == 404


@pytest.mark.parametrize("path", [ADMIN_LIST, CATALOG])
@pytest.mark.parametrize("page_token", INVALID_TOKENS)
async def test_invalid_page_token_is_rejected(
    client: AsyncClient, path: str, page_token: str
) -> None:
    response = await client.get(path, params={"page_token": page_token})

    assert response.status_code == 400
    assert response.json() == {"detail": "The page token is invalid."}
