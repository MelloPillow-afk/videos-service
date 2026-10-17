"""Jobs are read from PostgreSQL through the real application."""

from collections.abc import AsyncIterator
from uuid import uuid4

import psycopg
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def client(api_app: FastAPI, api_bearer_token: str) -> AsyncIterator[AsyncClient]:
    async with (
        api_app.router.lifespan_context(api_app),
        AsyncClient(
            transport=ASGITransport(app=api_app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {api_bearer_token}"},
        ) as client,
    ):
        yield client


async def insert_job(
    db: AsyncConnection, *, kind: str = "VIDEO_PROCESSING", status: str = "QUEUED", **values: object
) -> tuple[str, str]:
    job_id, content_id = str(values.get("id", uuid4())), str(values.get("content_id", uuid4()))
    await db.execute(
        "INSERT INTO jobs (id, content_id, kind, status, message) VALUES (%s, %s, %s, %s, %s)",
        (job_id, content_id, kind, status, values.get("message")),
    )
    return job_id, content_id


async def test_failed_job_reports_its_message(client: AsyncClient, db: AsyncConnection) -> None:
    job_id, content_id = await insert_job(
        db, status="FAILED", message="The source is not a valid MP4 video."
    )

    response = await client.get(f"/v1/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": job_id,
        "content_id": content_id,
        "status": "FAILED",
        "message": "The source is not a valid MP4 video.",
    }


async def test_missing_job_is_not_found(client: AsyncClient, db: AsyncConnection) -> None:
    await insert_job(db)

    response = await client.get(f"/v1/jobs/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "The job was not found."}


async def test_content_has_one_job_of_each_kind(db: AsyncConnection) -> None:
    _, content_id = await insert_job(db, kind="VIDEO_PROCESSING")
    await insert_job(db, kind="THUMBNAIL_GENERATION", content_id=content_id)

    with pytest.raises(psycopg.errors.UniqueViolation):
        await insert_job(db, kind="VIDEO_PROCESSING", content_id=content_id)


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
        "INSERT INTO jobs (content_id, kind) VALUES (%s, 'DELETION') "
        "RETURNING status, message, created_at = updated_at",
        (uuid4(),),
    )
    assert await cursor.fetchone() == ("QUEUED", None, True)
