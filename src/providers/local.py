"""Local development: runs worker jobs on this machine."""

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def run_job(job_id: UUID) -> None:
    # No local worker exists yet, so the job stays queued.
    logger.warning("No local worker is set up; job %s stays queued", job_id)
