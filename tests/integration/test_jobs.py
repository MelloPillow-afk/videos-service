"""Jobs are read from PostgreSQL through the real application."""

from uuid import uuid4

import psycopg
import pytest
from httpx import AsyncClient
from psycopg import AsyncConnection

from tests.utilities.rows import insert_video

pytestmark = pytest.mark.integration


async def insert_job(
    db: AsyncConnection, *, kind: str = "VIDEO_PROCESSING", status: str = "QUEUED", **values: object
) -> tuple[str, str]:
    job_id = str(values.get("id", uuid4()))
    video_id = str(values.get("video_id") or await insert_video(db))
    await db.execute(
        "INSERT INTO jobs (id, video_id, kind, status, message) VALUES (%s, %s, %s, %s, %s)",
        (job_id, video_id, kind, status, values.get("message")),
    )
    return job_id, video_id


async def test_failed_job_reports_its_message(client: AsyncClient, db: AsyncConnection) -> None:
    job_id, video_id = await insert_job(
        db, status="FAILED", message="The source is not a valid MP4 video."
    )

    response = await client.get(f"/v1/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": job_id,
        "video_id": video_id,
        "status": "FAILED",
        "message": "The source is not a valid MP4 video.",
    }


async def test_anyone_can_poll_a_job_without_a_token(
    client: AsyncClient, db: AsyncConnection
) -> None:
    job_id, _ = await insert_job(db)
    client.headers.pop("Authorization")

    response = await client.get(f"/v1/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "QUEUED"


async def test_missing_job_is_not_found(client: AsyncClient, db: AsyncConnection) -> None:
    await insert_job(db)

    response = await client.get(f"/v1/jobs/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "The job was not found."}


async def test_video_has_one_job_of_each_kind(db: AsyncConnection) -> None:
    _, video_id = await insert_job(db, kind="VIDEO_PROCESSING")
    await insert_job(db, kind="THUMBNAIL_GENERATION", video_id=video_id)

    with pytest.raises(psycopg.errors.UniqueViolation):
        await insert_job(db, kind="VIDEO_PROCESSING", video_id=video_id)


async def test_jobs_belong_to_an_existing_video(db: AsyncConnection) -> None:
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        await insert_job(db, video_id=uuid4())


async def test_removing_a_video_removes_its_jobs(db: AsyncConnection) -> None:
    job_id, video_id = await insert_job(db)

    await db.execute("DELETE FROM videos WHERE id = %s", (video_id,))

    cursor = await db.execute("SELECT count(*) FROM jobs WHERE id = %s", (job_id,))
    assert await cursor.fetchone() == (0,)


@pytest.mark.parametrize(
    "values",
    [
        {"status": "SUCCEEDED", "message": "Only failures explain themselves."},
        {"status": "CANCELLED"},
        {"kind": "TRANSCRIPTION"},
    ],
)
async def test_jobs_reject_invalid_states(db: AsyncConnection, values: dict[str, str]) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        await insert_job(db, **values)


async def test_new_jobs_default_to_queued(db: AsyncConnection) -> None:
    cursor = await db.execute(
        "INSERT INTO jobs (video_id, kind) VALUES (%s, 'DELETION') "
        "RETURNING status, message, created_at = updated_at",
        (await insert_video(db),),
    )
    assert await cursor.fetchone() == ("QUEUED", None, True)
