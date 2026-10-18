"""SQL access for the jobs table."""

from uuid import UUID

from psycopg.rows import TupleRow

from src.domain.jobs import Job, JobKind, JobStatus
from src.repositories.connections import db_connection

_COLUMNS = "id, video_id, kind, status, message, created_at, updated_at"


async def get_job(job_id: UUID) -> Job | None:
    async with db_connection() as conn:
        cursor = await conn.execute(f"SELECT {_COLUMNS} FROM jobs WHERE id = %s", (job_id,))
        row = await cursor.fetchone()
    return None if row is None else _job(row)


async def find_job(video_id: UUID, kind: JobKind) -> Job | None:
    """A video's job of one kind; each video has at most one."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            f"SELECT {_COLUMNS} FROM jobs WHERE video_id = %s AND kind = %s",
            (video_id, kind.value),
        )
        row = await cursor.fetchone()
    return None if row is None else _job(row)


async def start_job(job_id: UUID) -> Job | None:
    """Mark a queued job running; None when it is not queued."""
    async with db_connection() as conn:
        cursor = await conn.execute(
            "UPDATE jobs SET status = 'RUNNING', updated_at = now() "
            f"WHERE id = %s AND status = 'QUEUED' RETURNING {_COLUMNS}",
            (job_id,),
        )
        row = await cursor.fetchone()
    return None if row is None else _job(row)


async def fail_job(job_id: UUID, message: str) -> None:
    """Fail an unfinished job; a failed video job also fails its processing video."""
    async with db_connection() as conn:
        await conn.execute(
            "WITH failed AS ("
            "UPDATE jobs SET status = 'FAILED', message = %s, updated_at = now() "
            "WHERE id = %s AND status IN ('QUEUED', 'RUNNING') RETURNING video_id, kind"
            ") "
            "UPDATE videos SET status = 'FAILED', updated_at = now() FROM failed "
            "WHERE videos.id = failed.video_id AND failed.kind = 'VIDEO_PROCESSING' "
            "AND videos.status = 'PROCESSING'",
            (message, job_id),
        )


def _job(row: TupleRow) -> Job:
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
