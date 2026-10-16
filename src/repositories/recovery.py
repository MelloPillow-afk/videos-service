"""Processing retry and explicit operator recovery SQL; parent video locks come first."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from src.domain.videos import VideoConflict
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


async def prepare_relaunch(
    connection: AsyncConnection[TupleRow], job_id: UUID, *, previous_execution_terminated: bool
) -> bool:
    cursor = await connection.execute(
        "SELECT v.id,v.status FROM videos v JOIN jobs j ON j.video_id=v.id WHERE j.id=%s FOR UPDATE OF v",
        (job_id,),
    )
    video = await cursor.fetchone()
    if video is None:
        raise VideoConflict("The job was not found.")
    cursor = await connection.execute(
        "SELECT kind,state,is_current,execution_attempts FROM jobs WHERE id=%s FOR UPDATE",
        (job_id,),
    )
    job = await cursor.fetchone()
    assert job is not None
    kind, state, current, attempts = job
    if not current or ((kind == "DELETION") != (video[1] == "DELETING")):
        raise VideoConflict("The job is superseded or ineligible for its video state.")
    if state not in ("RECORDED", "LAUNCH_FAILED", "LAUNCHED", "RUNNING"):
        raise VideoConflict("Only stranded launches or interrupted executions can be relaunched.")
    if state == "RUNNING" and not previous_execution_terminated:
        raise VideoConflict(
            "Confirm the previous execution has terminated before recovering a running claim."
        )
    if state == "RUNNING":
        await connection.execute(
            """UPDATE jobs SET execution_history=execution_history || jsonb_build_array(
            jsonb_build_object('attempt',execution_attempts,'token',claim_token,'state','INTERRUPTED','at',now()))
            WHERE id=%s""",
            (job_id,),
        )
    if kind != "DELETION" and attempts >= 3:
        await connection.execute(
            "UPDATE jobs SET state='FAILED',error_code='EXECUTION_INTERRUPTED',error_message='The execution budget was exhausted after an interruption.',updated_at=now() WHERE id=%s",
            (job_id,),
        )
        if kind == "VIDEO":
            await connection.execute(
                "UPDATE videos SET status='FAILED',processing_error_code='EXECUTION_INTERRUPTED',processing_error_message='Processing was interrupted after its execution budget was exhausted.',updated_at=now() WHERE id=%s",
                (video[0],),
            )
        else:
            await connection.execute(
                "UPDATE videos SET generated_thumbnail_status='FAILED',updated_at=now() WHERE id=%s",
                (video[0],),
            )
        return False
    await connection.execute(
        "UPDATE jobs SET state='RECORDED',claim_token=NULL,updated_at=now() WHERE id=%s", (job_id,)
    )
    if kind == "VIDEO":
        await connection.execute(
            "UPDATE videos SET status='QUEUED',updated_at=now() WHERE id=%s", (video[0],)
        )

    return True
