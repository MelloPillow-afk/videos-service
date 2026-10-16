"""Shared-library video operations and transaction boundaries."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.videos import VideoConflict, VideoNotFound, VideoRecord
from src.repositories.database import Database
from src.repositories.videos import get_video, insert_video, save_metadata


def utc_now() -> datetime:
    return datetime.now(UTC)


class VideoService:
    def __init__(
        self,
        database: Database,
        *,
        clock: Callable[[], datetime] = utc_now,
        new_id: Callable[[], UUID] = uuid4,
    ) -> None:
        self.database = database
        self.clock = clock
        self.new_id = new_id

    async def create(self, title: str, description: str | None) -> VideoRecord:
        async with self.database.connection() as connection:
            return await insert_video(
                connection, id=self.new_id(), title=title, description=description, now=self.clock()
            )

    async def get(self, id: UUID, *, administrator: bool = False) -> VideoRecord:
        async with self.database.connection() as connection:
            video = await get_video(connection, id)
            if video is None or (
                not administrator
                and not (video.status == "READY" and video.publication_status == "PUBLISHED")
            ):
                raise VideoNotFound
            return video

    async def update(self, id: UUID, changes: dict[str, str | None]) -> VideoRecord:
        async with self.database.connection() as connection:
            video = await get_video(connection, id, for_update=True)
            if video is None:
                raise VideoNotFound
            if video.status == "DELETING":
                raise VideoConflict("The video is being deleted.")
            if "title" in changes:
                assert changes["title"] is not None
                video.title = changes["title"]
            if "description" in changes:
                video.description = changes["description"]
            if "publication_status" in changes:
                publication = changes["publication_status"]
                assert publication is not None
                if publication == "PUBLISHED" and video.status != "READY":
                    raise VideoConflict("Only ready videos can be published.")
                if publication != video.publication_status:
                    video.published_at = self.clock() if publication == "PUBLISHED" else None
                    video.publication_status = publication
            video.updated_at = self.clock()
            return await save_metadata(connection, video)
