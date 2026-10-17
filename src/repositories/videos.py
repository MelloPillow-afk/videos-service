"""SQL access for the videos table."""

from uuid import UUID

from psycopg.rows import TupleRow

from src.domain.videos import PublicationStatus, Video, VideoStatus
from src.repositories.connections import db_connection

_COLUMNS = (
    "videos.id, title, description, videos.status, publication_status, published_at, "
    "videos.created_at, videos.updated_at"
)


async def create_video(title: str, description: str | None) -> Video:
    async with db_connection() as conn:
        cursor = await conn.execute(
            # A new video has no processing job yet.
            f"INSERT INTO videos (title, description) VALUES (%s, %s) RETURNING {_COLUMNS}, NULL",
            (title, description),
        )
        row = await cursor.fetchone()
    assert row is not None  # INSERT ... RETURNING always yields the new row.
    return _video(row)


async def get_video(video_id: UUID) -> Video | None:
    async with db_connection() as conn:
        cursor = await conn.execute(
            f"SELECT {_COLUMNS}, jobs.id FROM videos "
            "LEFT JOIN jobs ON jobs.video_id = videos.id AND jobs.kind = 'VIDEO_PROCESSING' "
            "WHERE videos.id = %s AND videos.deleted_at IS NULL",
            (video_id,),
        )
        row = await cursor.fetchone()
    return None if row is None else _video(row)


def _video(row: TupleRow) -> Video:
    (
        id_,
        title,
        description,
        status,
        publication_status,
        published_at,
        created_at,
        updated_at,
        latest_job_id,
    ) = row
    return Video(
        id=id_,
        title=title,
        description=description,
        status=VideoStatus(status),
        publication_status=PublicationStatus(publication_status),
        published_at=published_at,
        created_at=created_at,
        updated_at=updated_at,
        latest_job_id=latest_job_id,
    )
