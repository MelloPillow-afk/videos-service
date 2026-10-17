"""HTTP handlers for background jobs."""

from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Path

from src.domain import jobs as domain
from src.schemas.generated.jobs import Job
from src.schemas.generated.operations import JobsGetJobJobIdParameter
from src.services import jobs as jobs_service


async def get_job(
    *,
    job_id: Annotated[JobsGetJobJobIdParameter, Path(alias="job_id", description="Job ID.")],
) -> Job:
    try:
        job = await jobs_service.get_job(UUID(job_id))
    except domain.JobNotFound:
        raise HTTPException(status_code=404, detail="The job was not found.") from None
    return job_resource(job)


def job_resource(job: domain.Job) -> Job:
    return Job(
        id=str(job.id),
        video_id=str(job.video_id),
        status=job.status.value,
        message=job.message,
    )
