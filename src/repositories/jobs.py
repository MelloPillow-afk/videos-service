"""SQL access for the jobs table."""

from uuid import UUID

from src.domain.jobs import Job, JobKind, JobStatus
from src.repositories.connections import db_connection


async def get_job(job_id: UUID) -> Job | None:
    async with db_connection() as conn:
        cursor = await conn.execute(
            "SELECT id, video_id, kind, status, message, created_at, updated_at "
            "FROM jobs WHERE id = %s",
            (job_id,),
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    id_, video_id, kind, status, message, created_at, updated_at = row
    return Job(
        id=id_,
        video_id=video_id,
        kind=JobKind(kind),
        status=JobStatus(status),
        message=message,
        created_at=created_at,
        updated_at=updated_at,
    )
