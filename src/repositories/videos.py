"""Video SQL operations; callers own the transaction."""

from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import TupleRow, class_row

from src.domain.videos import VideoRecord


async def insert_video(
    connection: AsyncConnection[TupleRow],
    *,
    id: UUID,
    title: str,
    description: str | None,
    now: datetime,
) -> VideoRecord:
    async with connection.cursor(row_factory=class_row(VideoRecord)) as cursor:
        await cursor.execute(
            """INSERT INTO videos (id, title, description, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s) RETURNING *""",
            (id, title, description, now, now),
        )
        result = await cursor.fetchone()
        assert result is not None
        return result


async def get_video(
    connection: AsyncConnection[TupleRow],
    id: UUID,
    *,
    for_update: bool = False,
) -> VideoRecord | None:
    async with connection.cursor(row_factory=class_row(VideoRecord)) as cursor:
        await cursor.execute(
            "SELECT * FROM videos WHERE id = %s" + (" FOR UPDATE" if for_update else ""), (id,)
        )
        return await cursor.fetchone()


async def save_metadata(connection: AsyncConnection[TupleRow], video: VideoRecord) -> VideoRecord:
    async with connection.cursor(row_factory=class_row(VideoRecord)) as cursor:
        await cursor.execute(
            """UPDATE videos SET title=%s, description=%s, publication_status=%s,
            published_at=%s, updated_at=%s WHERE id=%s RETURNING *""",
            (
                video.title,
                video.description,
                video.publication_status,
                video.published_at,
                video.updated_at,
                video.id,
            ),
        )
        result = await cursor.fetchone()
        assert result is not None
        return result
