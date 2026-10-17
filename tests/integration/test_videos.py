"""The videos table keeps each video in a valid lifecycle state."""

import psycopg
import pytest
from psycopg import AsyncConnection

from tests.utilities.rows import insert_video

pytestmark = pytest.mark.integration


async def test_new_videos_start_as_created_drafts(db: AsyncConnection) -> None:
    cursor = await db.execute(
        "INSERT INTO videos (title) VALUES ('Introduction to Faith') "
        "RETURNING status, publication_status, description, published_at, deleted_at, "
        "created_at = updated_at"
    )
    assert await cursor.fetchone() == ("CREATED", "DRAFT", None, None, None, True)


@pytest.mark.parametrize(
    "values",
    [
        {"status": "DELETING"},
        {"publication_status": "ARCHIVED"},
        {"publication_status": "PUBLISHED"},
        {"published_at": "2026-10-13T15:00:00Z"},
    ],
)
async def test_videos_reject_invalid_states(db: AsyncConnection, values: dict[str, str]) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        await insert_video(db, **values)


async def test_published_videos_record_when(db: AsyncConnection) -> None:
    await insert_video(
        db, status="READY", publication_status="PUBLISHED", published_at="2026-10-13T15:00:00Z"
    )
