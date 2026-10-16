"""Direct submission and explicit operator relaunch; no periodic dispatcher."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from src.domain.videos import VideoConflict
from src.providers.jobs import JobLauncher, JobLaunchError
from src.repositories.database import Database
from src.repositories.jobs import may_launch, record_launch
from src.repositories.recovery import (
    fail_interrupted_job,
    fail_interrupted_thumbnail,
    fail_interrupted_video,
    lock_recovery_snapshot,
    queue_interrupted_video,
    record_interrupted_execution,
    reset_job_for_relaunch,
)
from src.services.videos import utc_now


class JobSubmission:
    def __init__(
        self, database: Database, launcher: JobLauncher, *, clock: Callable[[], datetime] = utc_now
    ) -> None:
        self.database, self.launcher, self.clock = database, launcher, clock

    async def submit(self, job_id: UUID) -> bool:
        async with self.database.connection() as connection:
            if not await may_launch(connection, job_id):
                return False
        try:
            reference = await self.launcher.launch(job_id)
        except JobLaunchError:
            reference = None
        async with self.database.connection() as connection:
            await record_launch(connection, job_id, reference, self.clock())
        return reference is not None

    async def recover(self, job_id: UUID, *, previous_execution_terminated: bool = False) -> bool:
        async with self.database.connection() as connection:
            work = await lock_recovery_snapshot(connection, job_id)
            if work is None:
                raise VideoConflict("The job was not found.")
            cleanup = work.kind == "DELETION"
            if not work.is_current or cleanup != (work.video_status == "DELETING"):
                raise VideoConflict("The job is superseded or ineligible for its video state.")
            if work.state not in ("RECORDED", "LAUNCH_FAILED", "LAUNCHED", "RUNNING") and not (
                cleanup and work.state == "FAILED"
            ):
                raise VideoConflict(
                    "Only stranded launches or interrupted executions can be relaunched."
                )
            if work.state == "RUNNING" and not previous_execution_terminated:
                raise VideoConflict(
                    "Confirm the previous execution has terminated before recovering a running claim."
                )
            if work.state == "RUNNING":
                await record_interrupted_execution(connection, job_id)
            prepared = cleanup or work.execution_attempts < 3
            if prepared:
                await reset_job_for_relaunch(connection, job_id)
                if work.kind == "VIDEO":
                    await queue_interrupted_video(connection, work.video_id)
            else:
                await fail_interrupted_job(connection, job_id)
                if work.kind == "VIDEO":
                    await fail_interrupted_video(connection, work.video_id)
                else:
                    await fail_interrupted_thumbnail(connection, work.video_id)
        if not prepared:
            raise VideoConflict(
                "The media execution budget is exhausted; use an explicit video retry when eligible."
            )
        if not await self.submit(job_id):
            raise VideoConflict(
                "Launch was not confirmed; inspect cloud executions before another relaunch."
            )
        return True
