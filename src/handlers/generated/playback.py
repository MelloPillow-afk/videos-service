# Generated; do not edit.
# fmt: off
import json as _generator_json
from uuid import UUID as _generator_UUID

from src.core.generated.runtime import HandlerResponse as _generator_HandlerResponse
from src.core.generated.runtime import endpoint as _generator_endpoint
from src.core.generated.runtime import model_adapter as _generator_model_adapter
from src.schemas.generated.playback import Playback as _GetResourceResponse


@_generator_endpoint("playback.get_resource")
async def get_resource(*, id: _generator_UUID) -> _generator_HandlerResponse[_GetResourceResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.playback.Playback").validate_json(_generator_json.dumps({"playback": {"type": "hls", "url": "https://media.example.com/videos/intro/hls/master.m3u8"}, "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})
