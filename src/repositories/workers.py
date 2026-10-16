"""Conditional worker claims and publication SQL; service owns transactions."""

from dataclasses import dataclass
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import TupleRow, class_row
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class Work:
    id: UUID
    video_id: UUID
    source_key: str
    output_prefix: str
    attempt: int
    token: UUID


async def claim(connection: AsyncConnection[TupleRow], job_id: UUID, token: UUID) -> Work | None:
    # Every workflow locks the parent video first, then its job.
    cursor = await connection.execute(
        """SELECT v.id FROM videos v JOIN jobs j ON j.video_id=v.id
        WHERE j.id=%s FOR UPDATE OF v""",
        (job_id,),
    )
    if await cursor.fetchone() is None:
        return None
    async with connection.cursor(row_factory=class_row(Work)) as cursor:
        await cursor.execute(
            """UPDATE jobs j SET state='RUNNING', execution_attempts=execution_attempts+1,
            claim_token=%s,error_code=NULL,error_message=NULL, updated_at=now() FROM videos v
            WHERE j.id=%s AND j.video_id=v.id AND j.kind='VIDEO' AND j.is_current
            AND j.state IN ('RECORDED','LAUNCHED','LAUNCH_FAILED')
            AND v.status IN ('QUEUED','PROCESSING') AND v.source_key IS NOT NULL
            RETURNING j.id,j.video_id,v.source_key,j.output_prefix,
            j.execution_attempts AS attempt,j.claim_token AS token""",
            (token, job_id),
        )
        work = await cursor.fetchone()
    if work:
        await connection.execute(
            "UPDATE videos SET status='PROCESSING',updated_at=now() WHERE id=%s", (work.video_id,)
        )
    return work


async def eligible(connection: AsyncConnection[TupleRow], work: Work) -> bool:
    cursor = await connection.execute(
        "SELECT 1 FROM videos WHERE id=%s AND status='PROCESSING' FOR UPDATE",
        (work.video_id,),
    )
    if await cursor.fetchone() is None:
        return False
    cursor = await connection.execute(
        """SELECT 1 FROM jobs WHERE video_id=%s AND id=%s AND is_current
        AND state='RUNNING' AND claim_token=%s FOR UPDATE""",
        (work.video_id, work.id, work.token),
    )
    return await cursor.fetchone() is not None


async def register_outputs(
    connection: AsyncConnection[TupleRow], work: Work, keys: list[str]
) -> bool:
    if not await eligible(connection, work):
        return False
    await connection.execute(
        "UPDATE jobs SET output_keys=output_keys || %s,updated_at=now() WHERE id=%s",
        (Jsonb(keys), work.id),
    )
    return True


async def complete(
    connection: AsyncConnection[TupleRow],
    work: Work,
    master_key: str,
    duration: float,
    width: int,
    height: int,
) -> bool:
    if not await eligible(connection, work):
        return False
    await connection.execute(
        """UPDATE videos SET status='READY',source_validated=true,playback_key=%s,
        duration_seconds=%s,width=%s,height=%s,processing_error_code=NULL,
        processing_error_message=NULL,updated_at=now() WHERE id=%s""",
        (master_key, duration, width, height, work.video_id),
    )
    await connection.execute(
        "UPDATE jobs SET state='SUCCEEDED',updated_at=now() WHERE id=%s", (work.id,)
    )
    return True


async def fail(
    connection: AsyncConnection[TupleRow],
    work: Work,
    code: str,
    message: str,
    *,
    source_validated: bool = False,
) -> None:
    if not await eligible(connection, work):
        return
    await connection.execute(
        """UPDATE videos SET status='FAILED',source_validated=%s,processing_error_code=%s,
        processing_error_message=%s,updated_at=now() WHERE id=%s""",
        (source_validated, code, message, work.video_id),
    )
    await connection.execute(
        "UPDATE jobs SET state='FAILED',error_code=%s,error_message=%s,updated_at=now() WHERE id=%s",
        (code, message, work.id),
    )
