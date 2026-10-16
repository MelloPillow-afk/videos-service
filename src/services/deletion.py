"""Atomic deletion admission followed by direct cleanup submission."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.videos import VideoNotFound
from src.providers.jobs import JobLauncher
from src.repositories.database import Database
from src.repositories.deletion import current_cleanup, enter_deleting
from src.repositories.jobs import record_job
from src.repositories.videos import get_video
from src.services.job_recovery import JobSubmission
from src.services.videos import utc_now


class Deletions:
    def __init__(
        self,
        database: Database,
        launcher: JobLauncher,
        *,
        clock: Callable[[], datetime] = utc_now,
        new_id: Callable[[], UUID] = uuid4,
    ) -> None:
        self.database, self.launcher, self.clock, self.new_id = database, launcher, clock, new_id

    async def request(self, video_id: UUID) -> None:
        async with self.database.connection() as connection:
            video = await get_video(connection, video_id, for_update=True)
            if video is None:
                raise VideoNotFound
            existing = await current_cleanup(connection, video_id)
            if video.status == "DELETING" and existing is not None:
                return
            now = self.clock()
            await enter_deleting(connection, video_id, now)
            job = await record_job(
                connection, id=self.new_id(), video_id=video_id, kind="DELETION", now=now
            )
        await JobSubmission(self.database, self.launcher, clock=self.clock).submit(job.id)
