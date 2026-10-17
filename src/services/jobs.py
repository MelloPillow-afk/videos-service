"""Background jobs: reading them and starting their workers."""

import logging
from uuid import UUID

from src.config import Settings
from src.domain.jobs import Job, JobNotFound
from src.providers import gcp, local
from src.repositories import jobs as jobs_repository

logger = logging.getLogger(__name__)


async def get_job(job_id: UUID) -> Job:
    job = await jobs_repository.get_job(job_id)
    if job is None:
        raise JobNotFound(job_id)
    return job


async def launch(job_id: UUID, settings: Settings) -> None:
    """Start a queued job's worker; a job whose worker cannot start fails."""
    run_job = gcp.run_job if settings.api_env == "prod" else local.run_job
    try:
        await run_job(job_id)
    except Exception:
        logger.exception("Could not start job %s", job_id)
        await jobs_repository.fail_job(job_id, "The job could not be started.")
