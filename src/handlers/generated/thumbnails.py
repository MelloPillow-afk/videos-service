# Generated; do not edit.
# fmt: off
import json as _generator_json
from uuid import UUID as _generator_UUID

from src.core.generated.runtime import HandlerResponse as _generator_HandlerResponse
from src.core.generated.runtime import endpoint as _generator_endpoint
from src.core.generated.runtime import model_adapter as _generator_model_adapter
from src.schemas.generated.thumbnails import Thumbnail as _DeleteResourceResponse


@_generator_endpoint("thumbnails.delete_resource")
async def delete_resource(*, id: _generator_UUID) -> _generator_HandlerResponse[_DeleteResourceResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.thumbnails.Thumbnail").validate_json(_generator_json.dumps({"thumbnail": {"source": "CUSTOM", "status": "READY", "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg"}, "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})
