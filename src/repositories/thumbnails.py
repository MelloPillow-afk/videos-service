"""Custom-thumbnail SQL; the service owns every transaction boundary."""

from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from src.domain.uploads import UploadAttempt
from src.repositories.uploads import find_attempt


async def create_thumbnail_attempt(
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
        """UPDATE upload_attempts SET is_current=false,state='SUPERSEDED'
        WHERE video_id=%s AND kind='THUMBNAIL' AND is_current""",
        (video_id,),
    )
    await connection.execute(
        """INSERT INTO upload_attempts
        (id,video_id,kind,object_key,declared_size_bytes,content_type,expires_at,created_at)
        VALUES (%s,%s,'THUMBNAIL',%s,%s,%s,%s,%s)""",
        (id, video_id, key, size, content_type, expires_at, now),
    )
    attempt = await find_attempt(connection, id)
    assert attempt is not None
    return attempt


async def register_public_key(
    connection: AsyncConnection[TupleRow],
    id: UUID,
    key: str,
) -> None:
    await connection.execute(
        "UPDATE upload_attempts SET public_object_key=%s WHERE id=%s", (key, id)
    )


async def activate_custom_image(
    connection: AsyncConnection[TupleRow],
    attempt: UploadAttempt,
    key: str,
    now: datetime,
) -> None:
    await connection.execute(
        "UPDATE upload_attempts SET state='ACCEPTED',accepted_at=%s WHERE id=%s",
        (now, attempt.id),
    )
    await connection.execute(
        "UPDATE videos SET custom_thumbnail_key=%s,updated_at=%s WHERE id=%s",
        (key, now, attempt.video_id),
    )


async def remove_custom_image(
    connection: AsyncConnection[TupleRow],
    video_id: UUID,
    now: datetime,
) -> None:
    await connection.execute(
        """UPDATE upload_attempts SET is_current=false,state='REMOVED'
        WHERE video_id=%s AND kind='THUMBNAIL' AND is_current""",
        (video_id,),
    )
    await connection.execute(
        "UPDATE videos SET custom_thumbnail_key=NULL,updated_at=%s WHERE id=%s",
        (now, video_id),
    )
