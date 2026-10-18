"""HTTP handlers for playing videos."""

from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Path

from src.domain import videos as domain
from src.schemas.generated.operations import PlaybackGetPlaybackIdParameter
from src.schemas.generated.playback import Playback, PlaybackPlayback
from src.services import media as media_service
from src.services import videos as videos_service


async def get_playback(
    *,
    id: Annotated[PlaybackGetPlaybackIdParameter, Path(alias="id", description="Video ID.")],
) -> Playback:
    try:
        video = await videos_service.get_playable_video(UUID(id))
    except domain.VideoNotFound:
        raise HTTPException(status_code=404, detail="The video was not found.") from None
    except domain.VideoNotReady:
        raise HTTPException(status_code=409, detail="The video is not ready.") from None
    assert video.playback_key is not None  # A playable video has processed media.
    return Playback(
        video_id=str(video.id),
        playback=PlaybackPlayback(type="hls", url=media_service.media_url(video.playback_key)),
    )
