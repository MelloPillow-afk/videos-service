"""SQL access for the videos table."""

from src.domain.videos import PublicationStatus, Video, VideoStatus
from src.repositories.connections import db_connection


async def create_video(title: str, description: str | None) -> Video:
    async with db_connection() as conn:
        cursor = await conn.execute(
            "INSERT INTO videos (title, description) VALUES (%s, %s) "
            "RETURNING id, title, description, status, publication_status, published_at, "
            "created_at, updated_at",
            (title, description),
        )
        row = await cursor.fetchone()
    assert row is not None  # INSERT ... RETURNING always yields the new row.
    id_, title, description, status, publication_status, published_at, created_at, updated_at = row
    return Video(
        id=id_,
        title=title,
        description=description,
        status=VideoStatus(status),
        publication_status=PublicationStatus(publication_status),
        published_at=published_at,
        created_at=created_at,
        updated_at=updated_at,
        latest_job_id=None,
    )
