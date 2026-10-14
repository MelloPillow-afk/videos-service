# Generated; do not edit.
# fmt: off
import json as _generator_json
from uuid import UUID as _generator_UUID

from src.core.generated.runtime import HandlerResponse as _generator_HandlerResponse
from src.core.generated.runtime import endpoint as _generator_endpoint
from src.core.generated.runtime import model_adapter as _generator_model_adapter
from src.schemas.generated.uploads import SourceUpload as _CreateResourceResponse
from src.schemas.generated.uploads import SourceUploadCreate as _CreateResourceBody
from src.schemas.generated.uploads import (
    SourceUploadProcessing as _CompleteResourceResponse,
)
from src.schemas.generated.uploads import UploadComplete as _CompleteResourceBody


@_generator_endpoint("source_uploads.complete_resource")
async def complete_resource(*, id: _generator_UUID, body: _CompleteResourceBody) -> _generator_HandlerResponse[_CompleteResourceResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.uploads.SourceUploadProcessing").validate_json(_generator_json.dumps({"processing_job_id": "e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0", "status": "QUEUED", "thumbnail_status": "PENDING", "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})


@_generator_endpoint("source_uploads.create_resource")
async def create_resource(*, id: _generator_UUID, body: _CreateResourceBody) -> _generator_HandlerResponse[_CreateResourceResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.uploads.SourceUpload").validate_json(_generator_json.dumps({"status": "UPLOADING", "upload": {"expires_at": "2026-10-13T14:15:00Z", "headers": {"Content-Type": "video/mp4"}, "method": "PUT", "upload_id": "04d1790f-f941-4ba6-8d97-0e6830ca4394", "url": "https://uploads.example.com/source.mp4?signature=example"}, "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})
