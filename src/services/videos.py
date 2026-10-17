"""Business rules for managing videos."""

from src.domain.videos import Video
from src.repositories import videos as videos_repository


async def create_video(title: str, description: str | None) -> Video:
    return await videos_repository.create_video(title, description)
