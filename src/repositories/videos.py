"""SQL access for the videos table."""

from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from src.domain.jobs import JobKind, JobStatus
from src.domain.videos import PublicationStatus, Video, VideoStatus
from src.repositories.connections import db_connection

_COLUMNS = (
    "videos.id, title, description, videos.status, publication_status, published_at, "
    "videos.created_at, videos.updated_at, upload_id, source_key, size_bytes, "
    "duration_seconds, playback_key, generated_thumbnail_prefix, thumbnail_upload_id, "
    "thumbnail_upload_key, thumbnail_upload_size_bytes, custom_thumbnail_prefix"
)
# Each video has at most one job of each kind.
_JOBS = (
    "LEFT JOIN jobs ON jobs.video_id = videos.id AND jobs.kind = 'VIDEO_PROCESSING' "
    "LEFT JOIN jobs AS thumbnail_jobs ON thumbnail_jobs.video_id = videos.id "
    "AND thumbnail_jobs.kind = 'THUMBNAIL_GENERATION' "
)
_JOB_COLUMNS = "jobs.id, thumbnail_jobs.status"


async def create_video(title: str, description: str | None) -> Video:
    async with db_connection() as conn:
        cursor = await conn.execute(
            # A new video has no jobs yet.
            f"INSERT INTO videos (title, description) VALUES (%s, %s) RETURNING {_COLUMNS}, NULL, NULL",
            (title, description),
        )
        row = await cursor.fetchone()
    assert row is not None  # INSERT ... RETURNING always yields the new row.
    return _video(row)


async def get_video(video_id: UUID) -> Video | None:
    async with db_connection() as conn:
        cursor = await conn.execute(
            f"SELECT {_COLUMNS}, {_JOB_COLUMNS} FROM videos {_JOBS}"
            "WHERE videos.id = %s AND videos.deleted_at IS NULL",
            (video_id,),
        )
        row = await cursor.fetchone()
    return None if row is None else _video(row)


async def list_videos(
    publication_status: PublicationStatus | None,
    after: tuple[datetime, UUID] | None,
    limit: int,
) -> list[Video]:
    """Videos that have not been deleted, newest created first, after a (created_at, id)."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            f"SELECT {_COLUMNS}, {_JOB_COLUMNS} FROM videos {_JOBS}"
            "WHERE videos.deleted_at IS NULL "
            "AND (%(publication_status)s::text IS NULL "
            "OR publication_status = %(publication_status)s) "
            "AND (%(after_at)s::timestamptz IS NULL "
            "OR (videos.created_at, videos.id) < (%(after_at)s, %(after_id)s::uuid)) "
            "ORDER BY videos.created_at DESC, videos.id DESC LIMIT %(limit)s",
            {
                "publication_status": publication_status and publication_status.value,
                **_after(after),
                "limit": limit,
            },
        )
        rows = await cursor.fetchall()
    return [_video(row) for row in rows]


async def list_catalog_videos(after: tuple[datetime, UUID] | None, limit: int) -> list[Video]:
    """Ready, published videos that have not been deleted, newest published first,
    after a (published_at, id)."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            f"SELECT {_COLUMNS}, {_JOB_COLUMNS} FROM videos {_JOBS}"
            "WHERE videos.deleted_at IS NULL AND publication_status = 'PUBLISHED' "
            "AND videos.status = 'READY' "
            "AND (%(after_at)s::timestamptz IS NULL "
            "OR (published_at, videos.id) < (%(after_at)s, %(after_id)s::uuid)) "
            "ORDER BY published_at DESC, videos.id DESC LIMIT %(limit)s",
            {**_after(after), "limit": limit},
        )
        rows = await cursor.fetchall()
    return [_video(row) for row in rows]


async def update_video(video: Video) -> Video | None:
    """Save the editable fields of a video that has not been deleted."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            "WITH updated AS ("
            "UPDATE videos SET title = %s, description = %s, publication_status = %s, "
            "published_at = %s, updated_at = now() "
            "WHERE id = %s AND deleted_at IS NULL RETURNING *"
            ") "
            f"SELECT {_COLUMNS}, {_JOB_COLUMNS} FROM updated AS videos {_JOBS}",
            (
                video.title,
                video.description,
                video.publication_status.value,
                video.published_at,
                video.id,
            ),
        )
        row = await cursor.fetchone()
    return None if row is None else _video(row)


async def start_upload(video: Video) -> Video | None:
    """Save a video's new current upload, unless processing has already begun."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            "WITH updated AS ("
            "UPDATE videos SET status = %s, upload_id = %s, source_key = %s, size_bytes = %s, "
            "updated_at = now() "
            "WHERE id = %s AND deleted_at IS NULL AND status IN ('CREATED', 'UPLOADING') "
            "RETURNING *"
            ") "
            f"SELECT {_COLUMNS}, {_JOB_COLUMNS} FROM updated AS videos {_JOBS}",
            (
                video.status.value,
                video.upload_id,
                video.source_key,
                video.size_bytes,
                video.id,
            ),
        )
        row = await cursor.fetchone()
    return None if row is None else _video(row)


async def accept_upload(video: Video) -> dict[JobKind, UUID] | None:
    """Move an uploading video to processing and queue its video and thumbnail jobs
    together. None when its current upload changed or was already accepted."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE videos SET status = %s, size_bytes = %s, updated_at = now() "
            "WHERE id = %s AND upload_id = %s AND deleted_at IS NULL AND status = 'UPLOADING' "
            "RETURNING id",
            (video.status.value, video.size_bytes, video.id, video.upload_id),
        )
        if await cursor.fetchone() is None:
            return None
        cursor = await conn.execute(
            "INSERT INTO jobs (video_id, kind) "
            "VALUES (%(id)s, 'VIDEO_PROCESSING'), (%(id)s, 'THUMBNAIL_GENERATION') "
            "RETURNING kind, id",
            {"id": video.id},
        )
        rows = await cursor.fetchall()
    return {JobKind(kind): job_id for kind, job_id in rows}


async def finish_processing(video: Video, job_id: UUID) -> bool:
    """Save processed media and succeed the running video job together. False when the
    video is no longer processing the same upload, or the job is no longer running."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE videos SET status = %s, playback_key = %s, duration_seconds = %s, "
            "updated_at = now() "
            "WHERE id = %s AND upload_id = %s AND deleted_at IS NULL AND status = 'PROCESSING' "
            "RETURNING id",
            (
                video.status.value,
                video.playback_key,
                video.duration_seconds,
                video.id,
                video.upload_id,
            ),
        )
        return await cursor.fetchone() is not None and await _succeed_job(conn, job_id)


async def finish_thumbnail(video: Video, job_id: UUID) -> bool:
    """Save a generated thumbnail and succeed the running thumbnail job together. False
    when the video's upload changed or it was deleted, or the job is no longer running."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE videos SET generated_thumbnail_prefix = %s, updated_at = now() "
            "WHERE id = %s AND upload_id = %s AND deleted_at IS NULL RETURNING id",
            (video.generated_thumbnail_prefix, video.id, video.upload_id),
        )
        return await cursor.fetchone() is not None and await _succeed_job(conn, job_id)


async def start_thumbnail_upload(video: Video) -> Video | None:
    """Save a video's new current thumbnail upload, deleting the previous upload's job."""
    async with db_connection() as conn:
        await _delete_custom_thumbnail_job(conn, video.id)
        cursor = await conn.execute(
            "WITH updated AS ("
            "UPDATE videos SET thumbnail_upload_id = %s, thumbnail_upload_key = %s, "
            "thumbnail_upload_size_bytes = %s, updated_at = now() "
            "WHERE id = %s AND deleted_at IS NULL RETURNING *"
            ") "
            f"SELECT {_COLUMNS}, {_JOB_COLUMNS} FROM updated AS videos {_JOBS}",
            (
                video.thumbnail_upload_id,
                video.thumbnail_upload_key,
                video.thumbnail_upload_size_bytes,
                video.id,
            ),
        )
        row = await cursor.fetchone()
    return None if row is None else _video(row)


async def accept_thumbnail_upload(video: Video) -> UUID | None:
    """Save the uploaded thumbnail's size and queue its job together. None when the
    current thumbnail upload changed or was already accepted."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE videos SET thumbnail_upload_size_bytes = %s, updated_at = now() "
            "WHERE id = %s AND thumbnail_upload_id = %s AND deleted_at IS NULL RETURNING id",
            (video.thumbnail_upload_size_bytes, video.id, video.thumbnail_upload_id),
        )
        if await cursor.fetchone() is None:
            return None
        cursor = await conn.execute(
            "INSERT INTO jobs (video_id, kind) VALUES (%s, 'CUSTOM_THUMBNAIL_PROCESSING') "
            "ON CONFLICT (video_id, kind) DO NOTHING RETURNING id",
            (video.id,),
        )
        row = await cursor.fetchone()
        if row is None:
            await conn.rollback()
            return None
    return row[0]


async def finish_custom_thumbnail(video: Video, job_id: UUID) -> bool:
    """Show a rendered custom thumbnail and succeed its running job together. False when
    the thumbnail upload changed or was removed, the video was deleted, or the job is no
    longer running."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE videos SET custom_thumbnail_prefix = %s, updated_at = now() "
            "WHERE id = %s AND thumbnail_upload_id = %s AND deleted_at IS NULL RETURNING id",
            (video.custom_thumbnail_prefix, video.id, video.thumbnail_upload_id),
        )
        return await cursor.fetchone() is not None and await _succeed_job(conn, job_id)


async def remove_custom_thumbnail(video: Video) -> Video | None:
    """Clear a video's custom thumbnail and its current upload, deleting the upload's job."""
    async with db_connection() as conn:
        await _delete_custom_thumbnail_job(conn, video.id)
        cursor = await conn.execute(
            "WITH updated AS ("
            "UPDATE videos SET custom_thumbnail_prefix = %s, thumbnail_upload_id = %s, "
            "thumbnail_upload_key = %s, thumbnail_upload_size_bytes = %s, updated_at = now() "
            "WHERE id = %s AND deleted_at IS NULL RETURNING *"
            ") "
            f"SELECT {_COLUMNS}, {_JOB_COLUMNS} FROM updated AS videos {_JOBS}",
            (
                video.custom_thumbnail_prefix,
                video.thumbnail_upload_id,
                video.thumbnail_upload_key,
                video.thumbnail_upload_size_bytes,
                video.id,
            ),
        )
        row = await cursor.fetchone()
    return None if row is None else _video(row)


async def _delete_custom_thumbnail_job(conn: AsyncConnection[TupleRow], video_id: UUID) -> None:
    await conn.execute(
        "DELETE FROM jobs WHERE video_id = %s AND kind = 'CUSTOM_THUMBNAIL_PROCESSING'",
        (video_id,),
    )


async def _succeed_job(conn: AsyncConnection[TupleRow], job_id: UUID) -> bool:
    cursor = await conn.execute(
        "UPDATE jobs SET status = 'SUCCEEDED', updated_at = now() "
        "WHERE id = %s AND status = 'RUNNING' RETURNING id",
        (job_id,),
    )
    if await cursor.fetchone() is None:
        # Keep the video unchanged when its job was already finished.
        await conn.rollback()
        return False
    return True


async def delete_video(video_id: UUID) -> bool:
    """Mark a video deleted; its media and row are removed later by cleanup."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE videos SET deleted_at = now() "
            "WHERE id = %s AND deleted_at IS NULL RETURNING id",
            (video_id,),
        )
        row = await cursor.fetchone()
    return row is not None


def _after(after: tuple[datetime, UUID] | None) -> dict[str, object]:
    at, id_ = after or (None, None)
    return {"after_at": at, "after_id": id_}


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
        upload_id,
        source_key,
        size_bytes,
        duration_seconds,
        playback_key,
        generated_thumbnail_prefix,
        thumbnail_upload_id,
        thumbnail_upload_key,
        thumbnail_upload_size_bytes,
        custom_thumbnail_prefix,
        latest_job_id,
        thumbnail_job_status,
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
        upload_id=upload_id,
        source_key=source_key,
        size_bytes=size_bytes,
        duration_seconds=None if duration_seconds is None else float(duration_seconds),
        playback_key=playback_key,
        generated_thumbnail_prefix=generated_thumbnail_prefix,
        thumbnail_job_status=thumbnail_job_status and JobStatus(thumbnail_job_status),
        thumbnail_upload_id=thumbnail_upload_id,
        thumbnail_upload_key=thumbnail_upload_key,
        thumbnail_upload_size_bytes=thumbnail_upload_size_bytes,
        custom_thumbnail_prefix=custom_thumbnail_prefix,
    )
