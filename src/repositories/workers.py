"""Conditional worker claims and publication SQL; service owns transactions."""

from dataclasses import dataclass, replace
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import TupleRow, class_row
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class Work:
    id: UUID
    video_id: UUID
    kind: str
    source_key: str
    output_prefix: str
    attempt: int
    token: UUID


async def claim(
    connection: AsyncConnection[TupleRow], job_id: UUID, token: UUID, *, kind: str = "VIDEO"
) -> Work | None:
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
            WHERE j.id=%s AND j.video_id=v.id AND j.kind=%s AND j.is_current AND j.execution_attempts<3
            AND j.state IN ('RECORDED','LAUNCHED','LAUNCH_FAILED')
            AND ((j.kind='VIDEO' AND v.status IN ('QUEUED','PROCESSING')) OR (j.kind='THUMBNAIL' AND v.status<>'DELETING')) AND v.source_key IS NOT NULL
            RETURNING j.id,j.video_id,j.kind,v.source_key,j.output_prefix,
            j.execution_attempts AS attempt,j.claim_token AS token""",
            (token, job_id, kind),
        )
        work = await cursor.fetchone()
    if work and work.kind == "VIDEO":
        await connection.execute(
            "UPDATE videos SET status='PROCESSING',updated_at=now() WHERE id=%s", (work.video_id,)
        )
    if work:
        await history(connection, work, "RUNNING")
    return work


async def eligible(connection: AsyncConnection[TupleRow], work: Work) -> bool:
    cursor = await connection.execute(
        "SELECT 1 FROM videos WHERE id=%s AND status<>'DELETING' AND (%s<>'VIDEO' OR status='PROCESSING') FOR UPDATE",
        (work.video_id, work.kind),
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
    await history(connection, work, "SUCCEEDED")
    return True


async def history(
    connection: AsyncConnection[TupleRow], work: Work, state: str, code: str | None = None
) -> None:
    await connection.execute(
        """UPDATE jobs SET execution_history=execution_history || jsonb_build_array(
        jsonb_build_object('attempt', %s::int, 'token', %s::text, 'state', %s::text,
        'error_code', %s::text, 'at', now())) WHERE id=%s""",
        (work.attempt, str(work.token), state, code, work.id),
    )


async def next_attempt(
    connection: AsyncConnection[TupleRow], work: Work, token: UUID
) -> Work | None:
    if work.attempt >= 3 or not await eligible(connection, work):
        return None
    await connection.execute(
        """UPDATE jobs SET execution_attempts=execution_attempts+1,claim_token=%s,
        error_code=NULL,error_message=NULL,updated_at=now() WHERE id=%s""",
        (token, work.id),
    )
    next_work = replace(work, attempt=work.attempt + 1, token=token)
    await history(connection, next_work, "RUNNING")
    return next_work


async def fail(
    connection: AsyncConnection[TupleRow],
    work: Work,
    code: str,
    message: str,
    *,
    source_validated: bool = False,
    permanent: bool = True,
) -> bool | None:
    """True retries, False persisted failure, None fenced before any failure transition."""
    if not await eligible(connection, work):
        return None
    retry = not permanent and work.attempt < 3
    await history(connection, work, "TEMPORARY_FAILURE" if retry else "FAILED", code)
    await connection.execute(
        """UPDATE jobs SET state=%s,error_code=%s,error_message=%s,updated_at=now() WHERE id=%s""",
        ("RUNNING" if retry else "FAILED", code, message, work.id),
    )
    if work.kind == "VIDEO":
        await connection.execute(
            """UPDATE videos SET status=%s,source_validated=CASE WHEN %s THEN false ELSE source_validated OR %s END,
            processing_error_code=%s,processing_error_message=%s,updated_at=now() WHERE id=%s""",
            (
                "PROCESSING" if retry else "FAILED",
                permanent,
                source_validated,
                None if retry else code,
                None if retry else message,
                work.video_id,
            ),
        )
    elif not retry:
        await connection.execute(
            "UPDATE videos SET generated_thumbnail_status='FAILED',updated_at=now() WHERE id=%s",
            (work.video_id,),
        )
    return retry
