"""Admins upload a custom thumbnail directly to storage, complete the upload to render it,
and remove it to show the generated thumbnail again."""

import asyncio
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response
from psycopg import AsyncConnection

from tests.utilities.fakes import FakeLauncher, FakeStorage
from tests.utilities.media_urls import MEDIA_BASE_URL, expected_sizes
from tests.utilities.rows import insert_video

pytestmark = pytest.mark.integration

SIZE = 2048


async def start_upload(client: AsyncClient, video_id: str, size: int = SIZE) -> dict[str, Any]:
    response = await client.post(
        f"/v1/admin/videos/{video_id}/thumbnails:upload-url",
        json={"file_name": "cover.png", "content_type": "image/png", "size_bytes": size},
    )
    assert response.status_code == 200, response.text
    return response.json()["upload"]


async def upload(client: AsyncClient, storage: FakeStorage, video_id: str, size: int = SIZE) -> str:
    """Start a thumbnail upload and store its image; returns the upload ID."""
    upload_id = (await start_upload(client, video_id, size))["upload_id"]
    storage.files[f"videos/{video_id}/thumbnails/{upload_id}/source"] = bytes(size)
    return upload_id


async def complete(client: AsyncClient, video_id: str, upload_id: str) -> Response:
    return await client.post(
        f"/v1/admin/videos/{video_id}/thumbnails:complete-upload", json={"upload_id": upload_id}
    )


async def thumbnail_row(db: AsyncConnection, video_id: str) -> tuple[Any, ...] | None:
    cursor = await db.execute(
        "SELECT thumbnail_upload_id, thumbnail_upload_key, thumbnail_upload_size_bytes, "
        "custom_thumbnail_prefix FROM videos WHERE id = %s",
        (video_id,),
    )
    return await cursor.fetchone()


async def custom_jobs(db: AsyncConnection, video_id: str) -> list[tuple[Any, ...]]:
    cursor = await db.execute(
        "SELECT id, status FROM jobs WHERE video_id = %s AND kind = 'CUSTOM_THUMBNAIL_PROCESSING'",
        (video_id,),
    )
    return await cursor.fetchall()


@pytest.mark.parametrize("status", ["CREATED", "PROCESSING", "READY", "FAILED"])
async def test_upload_url_starts_a_thumbnail_upload_in_any_status(
    client: AsyncClient, db: AsyncConnection, status: str
) -> None:
    video_id = await insert_video(db, status=status)

    response = await client.post(
        f"/v1/admin/videos/{video_id}/thumbnails:upload-url",
        json={"file_name": "cover.png", "content_type": "image/png", "size_bytes": SIZE},
    )

    assert response.status_code == 200
    body = response.json()
    upload_id = body["upload"]["upload_id"]
    key = f"videos/{video_id}/thumbnails/{upload_id}/source"
    assert body == {
        "video_id": video_id,
        "upload": {
            "upload_id": upload_id,
            "method": "PUT",
            "url": f"https://uploads.example.com/{key}?signature=test",
            "headers": {"Content-Type": "image/png"},
            "expires_at": "2026-10-13T14:15:00Z",
        },
    }
    assert await thumbnail_row(db, video_id) == (UUID(upload_id), key, SIZE, None)


async def test_upload_of_an_unsupported_image_type_is_rejected(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(db)

    response = await client.post(
        f"/v1/admin/videos/{video_id}/thumbnails:upload-url",
        json={"file_name": "cover.gif", "content_type": "image/gif", "size_bytes": SIZE},
    )

    assert response.status_code == 422
    assert await thumbnail_row(db, video_id) == (None, None, None, None)


async def test_upload_larger_than_the_thumbnail_limit_is_rejected(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(db)

    response = await client.post(
        f"/v1/admin/videos/{video_id}/thumbnails:upload-url",
        json={"file_name": "cover.png", "content_type": "image/png", "size_bytes": 10_485_761},
    )

    assert response.status_code == 413
    assert await thumbnail_row(db, video_id) == (None, None, None, None)


@pytest.mark.parametrize(
    ("method", "action", "body"),
    [
        (
            "POST",
            ":upload-url",
            {"file_name": "c.png", "content_type": "image/png", "size_bytes": 1},
        ),
        ("POST", ":complete-upload", {"upload_id": str(uuid4())}),
        ("DELETE", "", None),
    ],
)
async def test_thumbnail_of_a_missing_video_is_not_found(
    client: AsyncClient, db: AsyncConnection, method: str, action: str, body: Any
) -> None:
    deleted = await insert_video(db, deleted_at="2026-10-13T14:00:00Z")

    for video_id in (str(uuid4()), deleted):
        response = await client.request(
            method, f"/v1/admin/videos/{video_id}/thumbnails{action}", json=body
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "The video was not found."}


async def test_completed_upload_queues_and_launches_rendering(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage, launcher: FakeLauncher
) -> None:
    video_id = await insert_video(db, status="READY")
    upload_id = await upload(client, storage, video_id)

    response = await complete(client, video_id, upload_id)

    assert response.status_code == 202
    job = response.json()
    assert response.headers["Location"] == f"/v1/jobs/{job['id']}"
    assert job == {"id": job["id"], "video_id": video_id, "status": "QUEUED", "message": None}
    assert await custom_jobs(db, video_id) == [(UUID(job["id"]), "QUEUED")]
    assert launcher.launched == [UUID(job["id"])]
    # The current thumbnail stays until rendering succeeds.
    video = (await client.get(f"/v1/admin/videos/{video_id}")).json()
    assert video["thumbnail"]["source"] == "NONE"


async def test_completing_again_returns_the_same_job(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage, launcher: FakeLauncher
) -> None:
    video_id = await insert_video(db)
    upload_id = await upload(client, storage, video_id)
    first = (await complete(client, video_id, upload_id)).json()

    response = await complete(client, video_id, upload_id)

    assert response.status_code == 202
    assert response.json() == first
    assert len(await custom_jobs(db, video_id)) == 1
    assert launcher.launched == [UUID(first["id"])]


async def test_thumbnail_that_cannot_start_fails_and_a_new_upload_can_retry(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage, launcher: FakeLauncher
) -> None:
    video_id = await insert_video(db, status="READY")
    path = f"/v1/admin/videos/{video_id}"
    before = (await client.get(path)).json()["thumbnail"]
    upload_id = await upload(client, storage, video_id)
    launcher.failing = {0}

    response = await complete(client, video_id, upload_id)

    assert response.status_code == 202
    job = response.json()
    assert job == {
        "id": job["id"],
        "video_id": video_id,
        "status": "FAILED",
        "message": "The job could not be started.",
    }
    assert (await client.get(f"/v1/jobs/{job['id']}")).json() == job
    assert (await client.get(path)).json()["thumbnail"] == before
    retry = await upload(client, storage, video_id)
    response = await complete(client, video_id, retry)
    assert response.json()["status"] == "QUEUED"
    assert launcher.launched == [UUID(response.json()["id"])]


async def test_concurrent_completions_start_rendering_once(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage, launcher: FakeLauncher
) -> None:
    video_id = await insert_video(db)
    upload_id = await upload(client, storage, video_id)

    responses = await asyncio.gather(*(complete(client, video_id, upload_id) for _ in range(5)))

    assert [response.status_code for response in responses] == [202] * 5
    assert len({response.json()["id"] for response in responses}) == 1
    assert len(await custom_jobs(db, video_id)) == 1
    assert len(launcher.launched) == 1


async def test_new_upload_url_replaces_the_current_upload_and_its_job(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage
) -> None:
    video_id = await insert_video(db)
    first = await upload(client, storage, video_id)
    assert (await complete(client, video_id, first)).status_code == 202

    second = (await start_upload(client, video_id))["upload_id"]

    row = await thumbnail_row(db, video_id)
    assert row is not None and row[0] == UUID(second)
    assert await custom_jobs(db, video_id) == []
    response = await complete(client, video_id, first)
    assert response.status_code == 409
    assert response.json() == {"detail": "This upload attempt is no longer current."}


async def test_completing_without_a_current_upload_is_rejected(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(db)

    response = await complete(client, video_id, str(uuid4()))

    assert response.status_code == 409


async def test_completing_before_the_image_is_stored_is_not_found(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(db)
    upload_id = (await start_upload(client, video_id))["upload_id"]

    response = await complete(client, video_id, upload_id)

    assert response.status_code == 404
    assert response.json() == {"detail": "The uploaded file was not found."}
    assert await custom_jobs(db, video_id) == []


async def test_stored_image_of_another_size_is_rejected(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage
) -> None:
    video_id = await insert_video(db)
    upload_id = await upload(client, storage, video_id)
    storage.files[f"videos/{video_id}/thumbnails/{upload_id}/source"] = bytes(SIZE + 1)

    response = await complete(client, video_id, upload_id)

    assert response.status_code == 409
    assert response.json() == {"detail": "The uploaded file's size differs from the declared size."}


async def test_stored_image_over_the_limit_is_rejected(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage, api_app: FastAPI
) -> None:
    video_id = await insert_video(db)
    upload_id = await upload(client, storage, video_id)
    settings = api_app.state.settings
    api_app.state.settings = settings.model_copy(update={"max_thumbnail_bytes": SIZE - 1})

    response = await complete(client, video_id, upload_id)

    assert response.status_code == 413
    assert await custom_jobs(db, video_id) == []


async def test_rendered_custom_thumbnail_replaces_the_generated_one(
    client: AsyncClient, db: AsyncConnection
) -> None:
    custom = f"videos/{uuid4()}/thumbnails/{uuid4()}"
    video_id = await insert_video(
        db,
        status="READY",
        publication_status="PUBLISHED",
        published_at="2026-10-13T14:00:00Z",
        generated_thumbnail_prefix="videos/v/uploads/u/thumbnails",
        custom_thumbnail_prefix=custom,
    )

    admin = (await client.get(f"/v1/admin/videos/{video_id}")).json()
    (catalog,) = (await client.get("/v1/videos")).json()["data"]

    expected = {
        "status": "READY",
        "source": "CUSTOM",
        "url": f"{MEDIA_BASE_URL}/{custom}/xl.jpg",
        "sizes": expected_sizes(custom),
    }
    assert admin["thumbnail"] == catalog["thumbnail"] == expected


async def test_delete_restores_the_generated_thumbnail(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage
) -> None:
    generated = "videos/v/uploads/u/thumbnails"
    video_id = await insert_video(
        db, generated_thumbnail_prefix=generated, custom_thumbnail_prefix="videos/v/thumbnails/t"
    )
    await db.execute(
        "INSERT INTO jobs (video_id, kind, status) VALUES (%s, 'THUMBNAIL_GENERATION', 'SUCCEEDED')",
        (video_id,),
    )
    pending = await upload(client, storage, video_id)
    assert (await complete(client, video_id, pending)).status_code == 202

    response = await client.delete(f"/v1/admin/videos/{video_id}/thumbnails")

    assert response.status_code == 200
    assert response.json() == {
        "video_id": video_id,
        "thumbnail": {
            "status": "READY",
            "source": "GENERATED",
            "url": f"{MEDIA_BASE_URL}/{generated}/xl.jpg",
            "sizes": expected_sizes(generated),
        },
    }
    assert await thumbnail_row(db, video_id) == (None, None, None, None)
    assert await custom_jobs(db, video_id) == []
    assert (await complete(client, video_id, pending)).status_code == 409


@pytest.mark.parametrize(
    ("generation", "expected_status"), [(None, "PENDING"), ("FAILED", "FAILED")]
)
async def test_delete_without_a_generated_thumbnail_shows_none(
    client: AsyncClient, db: AsyncConnection, generation: str | None, expected_status: str
) -> None:
    video_id = await insert_video(db, custom_thumbnail_prefix="videos/v/thumbnails/t")
    if generation:
        await db.execute(
            "INSERT INTO jobs (video_id, kind, status) VALUES (%s, 'THUMBNAIL_GENERATION', %s)",
            (video_id, generation),
        )

    response = await client.delete(f"/v1/admin/videos/{video_id}/thumbnails")

    assert response.status_code == 200
    assert response.json()["thumbnail"] == {
        "status": expected_status,
        "source": "NONE",
        "url": None,
        "sizes": None,
    }


async def test_delete_without_a_custom_thumbnail_changes_nothing(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(db)

    first = await client.delete(f"/v1/admin/videos/{video_id}/thumbnails")
    second = await client.delete(f"/v1/admin/videos/{video_id}/thumbnails")

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
