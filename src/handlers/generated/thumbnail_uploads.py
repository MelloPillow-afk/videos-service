# Generated; do not edit.
# fmt: off
import json
from uuid import UUID

from src.core.generated.runtime import HandlerResponse, endpoint, model_adapter
from src.schemas.generated.thumbnails import Thumbnail as _CompleteResourceResponse
from src.schemas.generated.thumbnails import ThumbnailUpload as _CreateResourceResponse
from src.schemas.generated.thumbnails import (
    ThumbnailUploadCreate as _CreateResourceBody,
)
from src.schemas.generated.uploads import UploadComplete as _CompleteResourceBody


@endpoint("thumbnail_uploads.complete_resource")
async def complete_resource(*, id: UUID, body: _CompleteResourceBody) -> HandlerResponse[_CompleteResourceResponse]:
    return HandlerResponse(payload=model_adapter("src.schemas.generated.thumbnails.Thumbnail").validate_json(json.dumps({"thumbnail": {"source": "CUSTOM", "status": "READY", "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg"}, "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})


@endpoint("thumbnail_uploads.create_resource")
async def create_resource(*, id: UUID, body: _CreateResourceBody) -> HandlerResponse[_CreateResourceResponse]:
    return HandlerResponse(payload=model_adapter("src.schemas.generated.thumbnails.ThumbnailUpload").validate_json(json.dumps({"upload": {"expires_at": "2026-10-13T14:15:00Z", "headers": {"Content-Type": "image/jpeg"}, "method": "PUT", "upload_id": "50fd0382-794f-4c9b-9a12-60e92a89e008", "url": "https://uploads.example.com/thumbnail.jpg?signature=example"}, "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})
