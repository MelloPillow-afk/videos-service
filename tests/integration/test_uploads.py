"""Admins upload a video's file directly to storage, then complete the upload to process it."""

from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from psycopg import AsyncConnection

from tests.fakes import FakeLauncher, FakeStorage
from tests.rows import insert_video

pytestmark = pytest.mark.integration

SIZE = 1024


async def start_upload(client: AsyncClient, video_id: str, size: int = SIZE) -> dict[str, Any]:
    response = await client.post(
        f"/v1/admin/videos/{video_id}:upload-url",
        json={"file_name": "intro.mp4", "content_type": "video/mp4", "size_bytes": size},
    )
    assert response.status_code == 200, response.text
    return response.json()["upload"]


async def upload(client: AsyncClient, storage: FakeStorage, video_id: str, size: int = SIZE) -> str:
    """Start an upload and store its file; returns the upload ID."""
    upload_id = (await start_upload(client, video_id, size))["upload_id"]
    storage.files[f"videos/{video_id}/uploads/{upload_id}/source.mp4"] = bytes(size)
    return upload_id


async def complete(client: AsyncClient, video_id: str, upload_id: str) -> Any:
    return await client.post(
        f"/v1/admin/videos/{video_id}:complete-upload", json={"upload_id": upload_id}
    )


async def video_row(db: AsyncConnection, video_id: str) -> tuple[Any, ...] | None:
    cursor = await db.execute(
        "SELECT status, upload_id, source_key, size_bytes FROM videos WHERE id = %s",
        (video_id,),
    )
    return await cursor.fetchone()


async def jobs(db: AsyncConnection, video_id: str) -> dict[str, tuple[Any, ...]]:
    cursor = await db.execute(
        "SELECT kind, id, status, message FROM jobs WHERE video_id = %s", (video_id,)
    )
    return {row[0]: tuple(row[1:]) for row in await cursor.fetchall()}


async def test_upload_url_starts_an_upload(client: AsyncClient, db: AsyncConnection) -> None:
    video_id = await insert_video(db)

    response = await client.post(
        f"/v1/admin/videos/{video_id}:upload-url",
        json={"file_name": "intro.mp4", "content_type": "video/mp4", "size_bytes": SIZE},
    )

    assert response.status_code == 200
    body = response.json()
    upload_id = body["upload"]["upload_id"]
    key = f"videos/{video_id}/uploads/{upload_id}/source.mp4"
    assert body == {
        "video_id": video_id,
        "status": "UPLOADING",
        "upload": {
            "upload_id": upload_id,
            "method": "PUT",
            "url": f"https://uploads.example.com/{key}?signature=test",
            "headers": {"Content-Type": "video/mp4"},
            "expires_at": "2026-10-13T14:15:00Z",
        },
    }
    assert await video_row(db, video_id) == ("UPLOADING", UUID(upload_id), key, SIZE)
    video = (await client.get(f"/v1/admin/videos/{video_id}")).json()
    assert (video["status"], video["size_bytes"]) == ("UPLOADING", SIZE)


async def test_new_upload_url_replaces_the_current_upload(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage
) -> None:
    video_id = await insert_video(db)
    first = await upload(client, storage, video_id)

    second = (await start_upload(client, video_id))["upload_id"]

    assert second != first
    row = await video_row(db, video_id)
    assert row is not None and row[1] == UUID(second)
    response = await complete(client, video_id, first)
    assert response.status_code == 409
    assert response.json() == {"detail": "This upload attempt is no longer current."}


async def test_upload_larger_than_the_limit_is_rejected(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(db)

    response = await client.post(
        f"/v1/admin/videos/{video_id}:upload-url",
        json={"file_name": "intro.mp4", "content_type": "video/mp4", "size_bytes": 104_857_601},
    )

    assert response.status_code == 413
    assert await video_row(db, video_id) == ("CREATED", None, None, None)


async def test_upload_url_for_a_missing_video_is_not_found(client: AsyncClient) -> None:
    response = await client.post(
        f"/v1/admin/videos/{uuid4()}:upload-url",
        json={"file_name": "intro.mp4", "content_type": "video/mp4", "size_bytes": SIZE},
    )

    assert response.status_code == 404


@pytest.mark.parametrize("status", ["PROCESSING", "READY", "FAILED"])
async def test_upload_url_after_processing_began_is_rejected(
    client: AsyncClient, db: AsyncConnection, status: str
) -> None:
    video_id = await insert_video(db, status=status)

    response = await client.post(
        f"/v1/admin/videos/{video_id}:upload-url",
        json={"file_name": "intro.mp4", "content_type": "video/mp4", "size_bytes": SIZE},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "The video is not eligible for this operation."}


async def test_completed_upload_queues_and_launches_processing(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage, launcher: FakeLauncher
) -> None:
    video_id = await insert_video(db)
    upload_id = await upload(client, storage, video_id)

    response = await complete(client, video_id, upload_id)

    assert response.status_code == 202
    job = response.json()
    assert response.headers["Location"] == f"/v1/jobs/{job['id']}"
    assert job == {"id": job["id"], "video_id": video_id, "status": "QUEUED", "message": None}
    video_job, thumbnail_job = (await jobs(db, video_id)).values()
    assert video_job == (UUID(job["id"]), "QUEUED", None)
    assert thumbnail_job[1:] == ("QUEUED", None)
    assert launcher.launched == [video_job[0], thumbnail_job[0]]
    video = (await client.get(f"/v1/admin/videos/{video_id}")).json()
    assert video["status"] == "PROCESSING"
    assert video["latest_job_id"] == job["id"]
    assert video["thumbnail"] == {"status": "PENDING", "source": "NONE", "url": None, "sizes": None}


async def test_completing_again_returns_the_same_job(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage, launcher: FakeLauncher
) -> None:
    video_id = await insert_video(db)
    upload_id = await upload(client, storage, video_id)
    first = (await complete(client, video_id, upload_id)).json()

    response = await complete(client, video_id, upload_id)

    assert response.status_code == 202
    assert response.json() == first
    assert len(launcher.launched) == 2
    assert len(await jobs(db, video_id)) == 2


async def test_completing_without_an_uploaded_file_is_not_found(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(db)
    upload_id = (await start_upload(client, video_id))["upload_id"]

    response = await complete(client, video_id, upload_id)

    assert response.status_code == 404
    assert response.json() == {"detail": "The uploaded file was not found."}
    row = await video_row(db, video_id)
    assert row is not None and row[0] == "UPLOADING"
    assert await jobs(db, video_id) == {}


@pytest.mark.parametrize(("stored_size", "status_code"), [(SIZE + 1, 409), (104_857_601, 413)])
async def test_uploaded_file_must_match_the_declared_size_and_limit(
    client: AsyncClient,
    db: AsyncConnection,
    storage: FakeStorage,
    stored_size: int,
    status_code: int,
) -> None:
    video_id = await insert_video(db)
    upload_id = await upload(client, storage, video_id)
    storage.files[f"videos/{video_id}/uploads/{upload_id}/source.mp4"] = bytes(stored_size)

    response = await complete(client, video_id, upload_id)

    assert response.status_code == status_code
    assert await video_row(db, video_id) == (
        "UPLOADING",
        UUID(upload_id),
        f"videos/{video_id}/uploads/{upload_id}/source.mp4",
        SIZE,
    )
    assert await jobs(db, video_id) == {}


async def test_completing_before_an_upload_starts_is_rejected(
    client: AsyncClient, db: AsyncConnection
) -> None:
    video_id = await insert_video(db)

    response = await complete(client, video_id, str(uuid4()))

    assert response.status_code == 409
    assert response.json() == {"detail": "The video is not eligible for this operation."}


async def test_completing_for_a_missing_video_is_not_found(client: AsyncClient) -> None:
    response = await complete(client, str(uuid4()), str(uuid4()))

    assert response.status_code == 404
    assert response.json() == {"detail": "The video was not found."}


async def test_video_that_cannot_start_processing_fails(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage, launcher: FakeLauncher
) -> None:
    video_id = await insert_video(db)
    upload_id = await upload(client, storage, video_id)
    launcher.failing = {0}  # The video job launches first.

    response = await complete(client, video_id, upload_id)

    assert response.status_code == 202
    assert response.json() | {"id": None} == {
        "id": None,
        "video_id": video_id,
        "status": "FAILED",
        "message": "The job could not be started.",
    }
    row = await video_row(db, video_id)
    assert row is not None and row[0] == "FAILED"
    assert (await jobs(db, video_id))["THUMBNAIL_GENERATION"][1] == "QUEUED"


async def test_thumbnail_that_cannot_start_does_not_fail_the_video(
    client: AsyncClient, db: AsyncConnection, storage: FakeStorage, launcher: FakeLauncher
) -> None:
    video_id = await insert_video(db)
    upload_id = await upload(client, storage, video_id)
    launcher.failing = {1}

    response = await complete(client, video_id, upload_id)

    assert response.json()["status"] == "QUEUED"
    video = (await client.get(f"/v1/admin/videos/{video_id}")).json()
    assert video["status"] == "PROCESSING"
    assert video["thumbnail"] == {"status": "FAILED", "source": "NONE", "url": None, "sizes": None}
