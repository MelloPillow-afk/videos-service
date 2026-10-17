"""Read access to background jobs."""

from uuid import UUID

from src.domain.jobs import Job, JobNotFound
from src.repositories import jobs as jobs_repository


async def get_job(job_id: UUID) -> Job:
    job = await jobs_repository.get_job(job_id)
    if job is None:
        raise JobNotFound(job_id)
    return job
