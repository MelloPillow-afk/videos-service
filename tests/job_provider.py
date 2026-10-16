"""Controlled external launch submission without executing media work."""

from uuid import UUID

from src.providers.jobs import JobLaunchError


class RecordingLauncher:
    def __init__(self) -> None:
        self.submissions: list[UUID] = []
        self.fail = False

    async def launch(self, job_id: UUID) -> str:
        self.submissions.append(job_id)
        if self.fail:
            raise JobLaunchError("controlled provider failure")
        return f"projects/test/locations/test/operations/{job_id}"
