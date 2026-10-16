"""Cleanup claim and completion SQL; transactions belong to the cleanup service."""

from dataclasses import dataclass, replace
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import TupleRow, class_row


@dataclass(frozen=True)
class CleanupWork:
    id: UUID
    video_id: UUID
    attempt: int
    token: UUID


async def lock_parent(connection: AsyncConnection[TupleRow], job_id: UUID) -> bool:
    cursor = await connection.execute(
        """SELECT v.id FROM videos v JOIN jobs j ON j.video_id=v.id
        WHERE j.id=%s AND v.status='DELETING' FOR UPDATE OF v""",
        (job_id,),
    )
    return await cursor.fetchone() is not None


async def claim(
    connection: AsyncConnection[TupleRow], job_id: UUID, token: UUID
) -> CleanupWork | None:
    if not await lock_parent(connection, job_id):
        return None
    async with connection.cursor(row_factory=class_row(CleanupWork)) as cursor:
        await cursor.execute(
            """UPDATE jobs SET state='RUNNING',execution_attempts=execution_attempts+1,
            claim_token=%s,error_code=NULL,error_message=NULL,updated_at=now()
            WHERE id=%s AND kind='DELETION' AND is_current
            AND state IN ('RECORDED','LAUNCHED','LAUNCH_FAILED')
            RETURNING id,video_id,execution_attempts AS attempt,claim_token AS token""",
            (token, job_id),
        )
        work = await cursor.fetchone()
    if work:
        await history(connection, work, "RUNNING")
    return work


async def eligible(connection: AsyncConnection[TupleRow], work: CleanupWork) -> bool:
    if not await lock_parent(connection, work.id):
        return False
    cursor = await connection.execute(
        """SELECT 1 FROM jobs WHERE id=%s AND video_id=%s AND kind='DELETION' AND is_current
        AND state='RUNNING' AND claim_token=%s FOR UPDATE""",
        (work.id, work.video_id, work.token),
    )
    return await cursor.fetchone() is not None


async def history(
    connection: AsyncConnection[TupleRow], work: CleanupWork, state: str, code: str | None = None
) -> None:
    await connection.execute(
        """UPDATE jobs SET execution_history=execution_history || jsonb_build_array(
        jsonb_build_object('attempt',%s::int,'token',%s::text,'state',%s::text,
        'error_code',%s::text,'at',now())) WHERE id=%s""",
        (work.attempt, str(work.token), state, code, work.id),
    )


async def failure(
    connection: AsyncConnection[TupleRow], work: CleanupWork, *, terminal: bool
) -> bool:
    if not await eligible(connection, work):
        return False
    code = "CLEANUP_RUNTIME_EXHAUSTED" if terminal else "CLEANUP_RETRYING"
    message = (
        "Cleanup runtime expired; inspect storage and explicitly recover this job."
        if terminal
        else "Cleanup could not verify every deletion guard; retrying."
    )
    await connection.execute(
        "UPDATE jobs SET state=%s,error_code=%s,error_message=%s,updated_at=now() WHERE id=%s",
        ("FAILED" if terminal else "RUNNING", code, message, work.id),
    )
    await history(connection, work, "FAILED" if terminal else "TEMPORARY_FAILURE", code)
    return True


async def next_attempt(
    connection: AsyncConnection[TupleRow], work: CleanupWork
) -> CleanupWork | None:
    if not await eligible(connection, work):
        return None
    await connection.execute(
        """UPDATE jobs SET execution_attempts=execution_attempts+1,
        error_code=NULL,error_message=NULL,updated_at=now() WHERE id=%s""",
        (work.id,),
    )
    following = replace(work, attempt=work.attempt + 1)
    await history(connection, following, "RUNNING")
    return following


async def complete(connection: AsyncConnection[TupleRow], work: CleanupWork) -> bool:
    if not await eligible(connection, work):
        return False
    # Cascades remove all three application-table records only after verified guards.
    await connection.execute("DELETE FROM videos WHERE id=%s", (work.video_id,))
    return True
