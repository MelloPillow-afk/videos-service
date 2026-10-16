"""Administrator processing retry creates one new current job with retained source."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.videos import VideoConflict, VideoNotFound, VideoRecord
from src.providers.jobs import JobLauncher
from src.providers.storage import Storage
from src.repositories.database import Database
from src.repositories.recovery import RetriedVideo, queue_retry
from src.repositories.videos import get_video
from src.services.job_recovery import JobSubmission
from src.services.videos import utc_now


class ProcessingRecovery:
    def __init__(
        self,
        database: Database,
        storage: Storage,
        launcher: JobLauncher,
        *,
        clock: Callable[[], datetime] = utc_now,
        new_id: Callable[[], UUID] = uuid4,
    ) -> None:
        self.database, self.storage = database, storage
        self.submission = JobSubmission(database, launcher, clock=clock)
        self.clock, self.new_id = clock, new_id

    @staticmethod
    def eligible(video: VideoRecord | None) -> VideoRecord:
        if video is None:
            raise VideoNotFound
        if video.status != "FAILED" or not video.source_validated or not video.source_key:
            raise VideoConflict(
                "Retry requires failed processing and a retained validated source. Invalid sources require deletion and recreation."
            )
        return video

    async def retry(self, video_id: UUID) -> RetriedVideo:
        async with self.database.connection() as connection:
            video = self.eligible(await get_video(connection, video_id))
        assert video.source_key
        observed = await self.storage.head("private", video.source_key)
        if observed is None or observed.size_bytes != video.size_bytes:
            raise VideoConflict("The validated source is no longer available.")
        async with self.database.connection() as connection:
            current = self.eligible(await get_video(connection, video_id, for_update=True))
            if current.source_key != video.source_key:
                raise VideoConflict("The retained source has changed.")
            result = await queue_retry(connection, video_id, self.new_id(), self.clock())
        await self.submission.submit(result.job_id)
        return result
