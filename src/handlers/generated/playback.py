# Generated; do not edit.
# fmt: off
import json
from uuid import UUID

from src.core.generated.runtime import HandlerResponse, endpoint, model_adapter
from src.schemas.generated.playback import Playback as _GetResourceResponse


@endpoint("playback.get_resource")
async def get_resource(*, id: UUID) -> HandlerResponse[_GetResourceResponse]:
    return HandlerResponse(payload=model_adapter("src.schemas.generated.playback.Playback").validate_json(json.dumps({"playback": {"type": "hls", "url": "https://media.example.com/videos/intro/hls/master.m3u8"}, "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})
