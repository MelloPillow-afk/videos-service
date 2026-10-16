"""Deletion acceptance SQL; physical cleanup policy is deliberately separate."""

from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import TupleRow, class_row

from src.domain.deletion import CleanupInventory, UploadWriter, WorkerWriter
from src.repositories.videos import get_video


async def current_cleanup(connection: AsyncConnection[TupleRow], video_id: UUID) -> UUID | None:
    cursor = await connection.execute(
        "SELECT id FROM jobs WHERE video_id=%s AND kind='DELETION' AND is_current", (video_id,)
    )
    row = await cursor.fetchone()
    return row[0] if row else None


async def enter_deleting(
    connection: AsyncConnection[TupleRow], video_id: UUID, now: datetime
) -> None:
    await connection.execute(
        "UPDATE videos SET status='DELETING',updated_at=%s WHERE id=%s", (now, video_id)
    )


async def mark_cleanup_policy_required(connection: AsyncConnection[TupleRow], job_id: UUID) -> None:
    await connection.execute(
        """UPDATE jobs SET error_code='CLEANUP_POLICY_REQUIRED',
        error_message='Cleanup is pending the approved writer-protection policy; media is not removed.'
        WHERE id=%s""",
        (job_id,),
    )


async def cleanup_inventory(
    connection: AsyncConnection[TupleRow],
    job_id: UUID,
) -> CleanupInventory | None:
    cursor = await connection.execute(
        "SELECT video_id FROM jobs WHERE id=%s AND kind='DELETION' AND is_current", (job_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    video = await get_video(connection, row[0])
    if video is None or video.status != "DELETING":
        return None
    async with connection.cursor(row_factory=class_row(UploadWriter)) as cursor:
        await cursor.execute(
            """SELECT id,kind,state,object_key,public_object_key,expires_at
            FROM upload_attempts WHERE video_id=%s ORDER BY id""",
            (video.id,),
        )
        uploads = await cursor.fetchall()
    async with connection.cursor(row_factory=class_row(WorkerWriter)) as cursor:
        await cursor.execute(
            """SELECT id,kind,state,execution_attempts,execution_reference,output_prefix,output_keys
            FROM jobs WHERE video_id=%s ORDER BY id""",
            (video.id,),
        )
        workers = await cursor.fetchall()
    private = {upload.object_key for upload in uploads}
    if video.source_key:
        private.add(video.source_key)
    public = {
        key
        for key in (video.playback_key, video.generated_thumbnail_key, video.custom_thumbnail_key)
        if key
    }
    public.update(upload.public_object_key for upload in uploads if upload.public_object_key)
    for worker in workers:
        public.update(worker.output_keys)
    prefixes = {f"videos/{video.id}/"} | {worker.output_prefix for worker in workers}
    return CleanupInventory(
        job_id,
        video.id,
        tuple(sorted(private)),
        tuple(sorted(public)),
        tuple(sorted(prefixes)),
        tuple(uploads),
        tuple(workers),
    )
