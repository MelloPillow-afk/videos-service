"""Durable direct-launch records; worker execution claims are independent."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from psycopg import AsyncConnection
from psycopg.rows import TupleRow


@dataclass(frozen=True)
class RecordedJob:
    id: UUID
    kind: str
    output_prefix: str


async def record_job(
    connection: AsyncConnection[TupleRow], *, id: UUID, video_id: UUID, kind: str, now: datetime
) -> RecordedJob:
    prefix = f"videos/{video_id}/jobs/{id}/"
    await connection.execute(
        """INSERT INTO jobs (id,video_id,kind,output_prefix,created_at,updated_at)
        VALUES (%s,%s,%s,%s,%s,%s)""",
        (id, video_id, kind, prefix, now, now),
    )
    return RecordedJob(id, kind, prefix)


async def source_processing_job(connection: AsyncConnection[TupleRow], upload_id: UUID) -> UUID:
    cursor = await connection.execute(
        """SELECT processing_job_id FROM upload_attempts WHERE id=%s AND state='ACCEPTED'""",
        (upload_id,),
    )
    result = await cursor.fetchone()
    assert result is not None
    return result[0]


async def record_launch(
    connection: AsyncConnection[TupleRow], id: UUID, reference: str | None, now: datetime
) -> None:
    if reference is not None:
        await connection.execute(
            """UPDATE jobs SET execution_reference=%s,
            state=CASE WHEN state IN ('RECORDED','LAUNCH_FAILED') THEN 'LAUNCHED' ELSE state END,
            updated_at=%s WHERE id=%s""",
            (reference, now, id),
        )
    else:
        await connection.execute(
            """UPDATE jobs SET state='LAUNCH_FAILED',error_code='LAUNCH_UNCONFIRMED',
            error_message='Launch was not confirmed; inspect executions before manual relaunch.',
            updated_at=%s WHERE id=%s AND state='RECORDED'""",
            (now, id),
        )


async def may_launch(connection: AsyncConnection[TupleRow], id: UUID) -> bool:
    cursor = await connection.execute(
        """SELECT 1 FROM jobs JOIN videos ON videos.id=jobs.video_id
        WHERE jobs.id=%s AND jobs.is_current AND videos.status <> 'DELETING'
        AND jobs.state IN ('RECORDED','LAUNCH_FAILED')""",
        (id,),
    )
    return await cursor.fetchone() is not None
