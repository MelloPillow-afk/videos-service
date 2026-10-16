"""Processing retry and explicit operator recovery SQL; parent video locks come first."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import TupleRow, class_row

from src.repositories.jobs import record_job


@dataclass(frozen=True)
class RetriedVideo:
    video_id: UUID
    job_id: UUID
    number: int


async def queue_retry(
    connection: AsyncConnection[TupleRow], video_id: UUID, job_id: UUID, now: datetime
) -> RetriedVideo:
    count = await connection.execute(
        "SELECT count(*) FROM jobs WHERE video_id=%s AND kind='VIDEO'", (video_id,)
    )
    row = await count.fetchone()
    assert row is not None
    number = max(2, row[0] + 1)
    await connection.execute(
        "UPDATE jobs SET is_current=false WHERE video_id=%s AND kind='VIDEO' AND is_current",
        (video_id,),
    )
    await record_job(connection, id=job_id, video_id=video_id, kind="VIDEO", now=now)
    await connection.execute(
        """UPDATE videos SET status='QUEUED',publication_status='DRAFT',published_at=NULL,
        playback_key=NULL,processing_error_code=NULL,processing_error_message=NULL,updated_at=%s WHERE id=%s""",
        (now, video_id),
    )
    return RetriedVideo(video_id, job_id, number)


@dataclass(frozen=True)
class LockedRecoverySnapshot:
    job_id: UUID
    video_id: UUID
    video_status: str
    kind: str
    state: str
    is_current: bool
    execution_attempts: int


async def lock_recovery_snapshot(
    connection: AsyncConnection[TupleRow], job_id: UUID
) -> LockedRecoverySnapshot | None:
    """The caller retains the transaction; always lock the parent before its job."""
    cursor = await connection.execute(
        "SELECT v.id,v.status FROM videos v JOIN jobs j ON j.video_id=v.id WHERE j.id=%s FOR UPDATE OF v",
        (job_id,),
    )
    video = await cursor.fetchone()
    if video is None:
        return None
    async with connection.cursor(row_factory=class_row(LockedRecoverySnapshot)) as cursor:
        await cursor.execute(
            """SELECT id AS job_id,video_id,%s::text AS video_status,
            kind,state,is_current,execution_attempts FROM jobs WHERE id=%s FOR UPDATE""",
            (video[1], job_id),
        )
        return await cursor.fetchone()


async def record_interrupted_execution(connection: AsyncConnection[TupleRow], job_id: UUID) -> None:
    await connection.execute(
        """UPDATE jobs SET execution_history=execution_history || jsonb_build_array(
        jsonb_build_object('attempt',execution_attempts,'token',claim_token,'state','INTERRUPTED','at',now()))
        WHERE id=%s AND state='RUNNING' AND is_current""",
        (job_id,),
    )


async def fail_interrupted_job(connection: AsyncConnection[TupleRow], job_id: UUID) -> None:
    await connection.execute(
        """UPDATE jobs SET state='FAILED',error_code='EXECUTION_INTERRUPTED',
        error_message='The execution budget was exhausted after an interruption.',updated_at=now()
        WHERE id=%s AND is_current""",
        (job_id,),
    )


async def fail_interrupted_video(connection: AsyncConnection[TupleRow], video_id: UUID) -> None:
    await connection.execute(
        """UPDATE videos SET status='FAILED',processing_error_code='EXECUTION_INTERRUPTED',
        processing_error_message='Processing was interrupted after its execution budget was exhausted.',
        updated_at=now() WHERE id=%s AND status <> 'DELETING'""",
        (video_id,),
    )


async def fail_interrupted_thumbnail(connection: AsyncConnection[TupleRow], video_id: UUID) -> None:
    await connection.execute(
        """UPDATE videos SET generated_thumbnail_status='FAILED',updated_at=now()
        WHERE id=%s AND status <> 'DELETING'""",
        (video_id,),
    )


async def reset_job_for_relaunch(connection: AsyncConnection[TupleRow], job_id: UUID) -> None:
    await connection.execute(
        """UPDATE jobs SET state='RECORDED',claim_token=NULL,updated_at=now()
        WHERE id=%s AND is_current""",
        (job_id,),
    )


async def queue_interrupted_video(connection: AsyncConnection[TupleRow], video_id: UUID) -> None:
    await connection.execute(
        "UPDATE videos SET status='QUEUED',updated_at=now() WHERE id=%s AND status <> 'DELETING'",
        (video_id,),
    )
