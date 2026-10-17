"""Business rules for managing videos."""

from uuid import UUID

from src.domain.videos import Video, VideoNotFound
from src.repositories import videos as videos_repository


async def create_video(title: str, description: str | None) -> Video:
    return await videos_repository.create_video(title, description)


async def get_video(video_id: UUID) -> Video:
    video = await videos_repository.get_video(video_id)
    if video is None:
        raise VideoNotFound(video_id)
    return video
