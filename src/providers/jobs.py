"""Direct external job submission; execution remains independent of the API."""

from typing import Protocol
from uuid import UUID


class JobLaunchError(Exception):
    pass


class JobLauncher(Protocol):
    async def launch(self, job_id: UUID) -> str: ...
