# Generated; do not edit.
# fmt: off
import json
from uuid import UUID

from src.core.generated.runtime import HandlerResponse, endpoint, model_adapter
from src.schemas.generated.uploads import SourceUpload as _CreateResourceResponse
from src.schemas.generated.uploads import SourceUploadCreate as _CreateResourceBody
from src.schemas.generated.uploads import (
    SourceUploadProcessing as _CompleteResourceResponse,
)
from src.schemas.generated.uploads import UploadComplete as _CompleteResourceBody


@endpoint("source_uploads.complete_resource")
async def complete_resource(*, id: UUID, body: _CompleteResourceBody) -> HandlerResponse[_CompleteResourceResponse]:
    return HandlerResponse(payload=model_adapter("src.schemas.generated.uploads.SourceUploadProcessing").validate_json(json.dumps({"processing_job_id": "e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0", "status": "QUEUED", "thumbnail_status": "PENDING", "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})


@endpoint("source_uploads.create_resource")
async def create_resource(*, id: UUID, body: _CreateResourceBody) -> HandlerResponse[_CreateResourceResponse]:
    return HandlerResponse(payload=model_adapter("src.schemas.generated.uploads.SourceUpload").validate_json(json.dumps({"status": "UPLOADING", "upload": {"expires_at": "2026-10-13T14:15:00Z", "headers": {"Content-Type": "video/mp4"}, "method": "PUT", "upload_id": "04d1790f-f941-4ba6-8d97-0e6830ca4394", "url": "https://uploads.example.com/source.mp4?signature=example"}, "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})
