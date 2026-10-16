"""Direct submission and explicit operator relaunch; no periodic dispatcher."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from src.domain.videos import VideoConflict
from src.providers.jobs import JobLauncher, JobLaunchError
from src.repositories.database import Database
from src.repositories.jobs import may_launch, record_launch
from src.repositories.recovery import prepare_relaunch
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
            prepared = await prepare_relaunch(
                connection, job_id, previous_execution_terminated=previous_execution_terminated
            )
        if not prepared:
            raise VideoConflict(
                "The media execution budget is exhausted; use an explicit video retry when eligible."
            )
        if not await self.submit(job_id):
            raise VideoConflict(
                "Launch was not confirmed; inspect cloud executions before another relaunch."
            )
        return True
