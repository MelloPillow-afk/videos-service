# Generated; do not edit.
# fmt: off
import json as _generator_json
from uuid import UUID as _generator_UUID

from src.core.generated.runtime import HandlerResponse as _generator_HandlerResponse
from src.core.generated.runtime import endpoint as _generator_endpoint
from src.core.generated.runtime import model_adapter as _generator_model_adapter
from src.schemas.generated.thumbnails import Thumbnail as _CompleteResourceResponse
from src.schemas.generated.thumbnails import ThumbnailUpload as _CreateResourceResponse
from src.schemas.generated.thumbnails import (
    ThumbnailUploadCreate as _CreateResourceBody,
)
from src.schemas.generated.uploads import UploadComplete as _CompleteResourceBody


@_generator_endpoint("thumbnail_uploads.complete_resource")
async def complete_resource(*, id: _generator_UUID, body: _CompleteResourceBody) -> _generator_HandlerResponse[_CompleteResourceResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.thumbnails.Thumbnail").validate_json(_generator_json.dumps({"thumbnail": {"source": "CUSTOM", "status": "READY", "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg"}, "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})


@_generator_endpoint("thumbnail_uploads.create_resource")
async def create_resource(*, id: _generator_UUID, body: _CreateResourceBody) -> _generator_HandlerResponse[_CreateResourceResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.thumbnails.ThumbnailUpload").validate_json(_generator_json.dumps({"upload": {"expires_at": "2026-10-13T14:15:00Z", "headers": {"Content-Type": "image/jpeg"}, "method": "PUT", "upload_id": "50fd0382-794f-4c9b-9a12-60e92a89e008", "url": "https://uploads.example.com/thumbnail.jpg?signature=example"}, "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})
