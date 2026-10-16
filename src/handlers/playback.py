"""HLS discovery; clients fetch media directly from public delivery."""

from uuid import UUID

from fastapi import HTTPException, Request

from src.domain.videos import VideoConflict, VideoNotFound
from src.handlers.dependencies import optional_admin
from src.handlers.video_projection import delivery_url
from src.schemas.generated.operations import PlaybackGetPlaybackIdParameter
from src.schemas.generated.playback import Playback
from src.services.videos import VideoService


async def get_playback(*, id: PlaybackGetPlaybackIdParameter, request: Request) -> Playback:
    service: VideoService = request.app.state.videos
    try:
        video = await service.playback(UUID(id), administrator=await optional_admin(request))
    except VideoNotFound:
        raise HTTPException(404, "The video was not found.") from None
    except VideoConflict as error:
        raise HTTPException(409, str(error)) from None
    assert video.playback_key is not None
    return Playback.model_validate(
        {
            "video_id": str(video.id),
            "playback": {
                "type": "hls",
                "url": delivery_url(request.app.state.settings.cdn_origin, video.playback_key),
            },
        }
    )
