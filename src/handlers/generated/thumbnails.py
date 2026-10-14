# Generated; do not edit.
# fmt: off
import json
from uuid import UUID

from src.core.generated.runtime import HandlerResponse, endpoint, model_adapter
from src.schemas.generated.thumbnails import Thumbnail as _DeleteResourceResponse


@endpoint("thumbnails.delete_resource")
async def delete_resource(*, id: UUID) -> HandlerResponse[_DeleteResourceResponse]:
    return HandlerResponse(payload=model_adapter("src.schemas.generated.thumbnails.Thumbnail").validate_json(json.dumps({"thumbnail": {"source": "CUSTOM", "status": "READY", "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg"}, "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})
