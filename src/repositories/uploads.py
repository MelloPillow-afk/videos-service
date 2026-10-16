"""Source upload SQL operations; services own transaction scopes."""

from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import TupleRow, class_row

from src.domain.uploads import UploadAttempt


async def find_attempt(connection: AsyncConnection[TupleRow], id: UUID) -> UploadAttempt | None:
    async with connection.cursor(row_factory=class_row(UploadAttempt)) as cursor:
        await cursor.execute(
            """SELECT id,video_id,kind,object_key,declared_size_bytes,content_type,expires_at,
                is_current,state,accepted_at,created_at FROM upload_attempts WHERE id=%s""",
            (id,),
        )
        return await cursor.fetchone()


async def create_attempt(
    connection: AsyncConnection[TupleRow],
    *,
    id: UUID,
    video_id: UUID,
    key: str,
    size: int,
    content_type: str,
    expires_at: datetime,
    now: datetime,
) -> UploadAttempt:
    await connection.execute(
        """UPDATE upload_attempts SET is_current=false, state='SUPERSEDED'
        WHERE video_id=%s AND kind='SOURCE' AND is_current""",
        (video_id,),
    )
    async with connection.cursor(row_factory=class_row(UploadAttempt)) as cursor:
        await cursor.execute(
            """INSERT INTO upload_attempts
            (id,video_id,kind,object_key,declared_size_bytes,content_type,expires_at,created_at)
            VALUES (%s,%s,'SOURCE',%s,%s,%s,%s,%s) RETURNING *""",
            (id, video_id, key, size, content_type, expires_at, now),
        )
        result = await cursor.fetchone()
        assert result is not None
    await connection.execute(
        "UPDATE videos SET status='UPLOADING',updated_at=%s WHERE id=%s", (now, video_id)
    )
    return result


async def accept_attempt(
    connection: AsyncConnection[TupleRow], attempt: UploadAttempt, now: datetime
) -> None:
    await connection.execute(
        "UPDATE upload_attempts SET state='ACCEPTED',accepted_at=%s WHERE id=%s", (now, attempt.id)
    )
    await connection.execute(
        """UPDATE videos SET status='QUEUED',source_key=%s,size_bytes=%s,
        generated_thumbnail_status='PENDING',updated_at=%s WHERE id=%s""",
        (attempt.object_key, attempt.declared_size_bytes, now, attempt.video_id),
    )
