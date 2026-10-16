"""Admission-only source uploads, verified acceptance, and direct job submission."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import TupleRow

from src.config import Settings
from src.domain.uploads import SourceAccepted, UploadAttempt, UploadRejected
from src.domain.videos import VideoConflict, VideoNotFound, VideoRecord
from src.providers.jobs import JobLauncher, JobLaunchError
from src.providers.storage import Storage, UploadInstructions
from src.repositories.database import Database
from src.repositories.jobs import may_launch, record_job, record_launch, source_processing_job
from src.repositories.uploads import accept_attempt, create_attempt, find_attempt
from src.repositories.videos import get_video
from src.services.videos import utc_now


@dataclass(frozen=True)
class SourceInstructions:
    attempt: UploadAttempt
    upload: UploadInstructions


class SourceUploads:
    def __init__(
        self,
        database: Database,
        storage: Storage,
        launcher: JobLauncher,
        settings: Settings,
        *,
        clock: Callable[[], datetime] = utc_now,
        new_id: Callable[[], UUID] = uuid4,
    ) -> None:
        self.database, self.storage, self.launcher, self.settings = (
            database,
            storage,
            launcher,
            settings,
        )
        self.clock, self.new_id = clock, new_id

    @staticmethod
    def eligible(video: VideoRecord | None) -> VideoRecord:
        if video is None:
            raise VideoNotFound
        if video.status not in ("CREATED", "UPLOADING"):
            raise VideoConflict("Source uploads require a created or uploading video.")
        return video

    async def issue(self, video_id: UUID, content_type: str, size: int) -> SourceInstructions:
        if size > self.settings.source_max_bytes:
            raise UploadRejected("too_large", "The file exceeds the configured size limit.")
        async with self.database.connection() as connection:
            self.eligible(await get_video(connection, video_id))
        id, now = self.new_id(), self.clock()
        key = f"videos/{video_id}/uploads/{id}/source.mp4"
        instructions = await self.storage.sign_upload(key, content_type, 900)
        async with self.database.connection() as connection:
            self.eligible(await get_video(connection, video_id, for_update=True))
            attempt = await create_attempt(
                connection,
                id=id,
                video_id=video_id,
                key=key,
                size=size,
                content_type=content_type,
                expires_at=now + timedelta(minutes=15),
                now=now,
            )
        return SourceInstructions(attempt, instructions)

    @staticmethod
    def current(
        video: VideoRecord | None, attempt: UploadAttempt | None, video_id: UUID
    ) -> UploadAttempt:
        if video is None:
            raise VideoNotFound
        if video.status == "DELETING":
            raise VideoConflict("The video is being deleted.")
        if attempt is None or attempt.video_id != video_id or attempt.kind != "SOURCE":
            raise VideoConflict("The source upload attempt is not current.")
        if not attempt.is_current or attempt.state not in ("PENDING", "ACCEPTED"):
            raise VideoConflict("The source upload attempt is not current.")
        return attempt

    async def _accepted(
        self, connection: AsyncConnection[TupleRow], video: VideoRecord
    ) -> SourceAccepted:
        return SourceAccepted(
            video.id,
            video.status,
            await source_processing_job(connection, video.id),
            video.generated_thumbnail_status,
        )

    async def confirm(self, video_id: UUID, upload_id: UUID) -> SourceAccepted:
        async with self.database.connection() as connection:
            video = await get_video(connection, video_id)
            attempt = self.current(video, await find_attempt(connection, upload_id), video_id)
            if attempt.state == "ACCEPTED":
                assert video is not None
                return await self._accepted(connection, video)
            self.eligible(video)
        observed = await self.storage.head("private", attempt.object_key)
        if observed is None:
            raise UploadRejected("missing", "The uploaded file was not found.")
        if observed.size_bytes > self.settings.source_max_bytes:
            raise UploadRejected("too_large", "The file exceeds the configured size limit.")
        if observed.size_bytes != attempt.declared_size_bytes:
            raise UploadRejected("invalid", "The uploaded size does not match the declared size.")
        if observed.content_type != attempt.content_type:
            raise UploadRejected(
                "invalid", "The uploaded media type does not match the declared type."
            )
        async with self.database.connection() as connection:
            video = await get_video(connection, video_id, for_update=True)
            attempt = self.current(video, await find_attempt(connection, upload_id), video_id)
            assert video is not None
            if attempt.state == "ACCEPTED":
                return await self._accepted(connection, video)
            self.eligible(video)
            now = self.clock()
            video_job = await record_job(
                connection, id=self.new_id(), video_id=video_id, kind="VIDEO", now=now
            )
            thumbnail_job = await record_job(
                connection, id=self.new_id(), video_id=video_id, kind="THUMBNAIL", now=now
            )
            await accept_attempt(connection, attempt, now)
        await asyncio.gather(self.launch(video_job.id), self.launch(thumbnail_job.id))
        async with self.database.connection() as connection:
            video = await get_video(connection, video_id)
            if video is None or video.status == "DELETING":
                raise VideoConflict("The video is being deleted.")
            return await self._accepted(connection, video)

    async def launch(self, id: UUID) -> None:
        async with self.database.connection() as connection:
            if not await may_launch(connection, id):
                return
        try:
            reference = await self.launcher.launch(id)
        except JobLaunchError:
            reference = None
        async with self.database.connection() as connection:
            await record_launch(connection, id, reference, self.clock())
