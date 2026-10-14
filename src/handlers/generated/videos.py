# Generated; do not edit.
# fmt: off
import json as _generator_json
from uuid import UUID as _generator_UUID

from src.core.generated.runtime import HandlerResponse as _generator_HandlerResponse
from src.core.generated.runtime import endpoint as _generator_endpoint
from src.core.generated.runtime import model_adapter as _generator_model_adapter
from src.schemas.generated.operations import (
    VideosGetCollectionCursorParameter as _GetCollectionCursorParameter,
)
from src.schemas.generated.operations import (
    VideosGetCollectionLimitParameter as _GetCollectionLimitParameter,
)
from src.schemas.generated.operations import (
    VideosGetCollectionSearchParameter as _GetCollectionSearchParameter,
)
from src.schemas.generated.videos import (
    PublicationStatus as _GetCollectionPublicationStatusParameter,
)
from src.schemas.generated.videos import Video as _CreateResourceResponse
from src.schemas.generated.videos import Video as _GetResourceResponse
from src.schemas.generated.videos import Video as _UpdateResourceResponse
from src.schemas.generated.videos import VideoCreate as _CreateResourceBody
from src.schemas.generated.videos import VideoDeletion as _DeleteResourceResponse
from src.schemas.generated.videos import VideoRetry as _RetryProcessingResponse
from src.schemas.generated.videos import Videos as _GetCollectionResponse
from src.schemas.generated.videos import VideoStatus as _GetCollectionStatusParameter
from src.schemas.generated.videos import VideoUpdate as _UpdateResourceBody


@_generator_endpoint("videos.get_collection")
async def get_collection(*, cursor: _GetCollectionCursorParameter | None = None, limit: _GetCollectionLimitParameter = 20, publication_status: _GetCollectionPublicationStatusParameter | None = None, search: _GetCollectionSearchParameter | None = None, status: _GetCollectionStatusParameter | None = None) -> _generator_HandlerResponse[_GetCollectionResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.videos.Videos").validate_json(_generator_json.dumps({"data": [{"created_at": "2026-10-13T14:00:00Z", "description": "An introductory lesson", "duration_seconds": 1475.5, "id": "550e8400-e29b-41d4-a716-446655440000", "publication_status": "PUBLISHED", "published_at": "2026-10-13T15:00:00Z", "size_bytes": 524288000, "status": "READY", "thumbnail": {"source": "CUSTOM", "status": "READY", "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg"}, "title": "Introduction to Faith", "updated_at": "2026-10-13T15:00:00Z"}], "pagination": {"has_more": True, "next_page_token": "example_next_page_token"}}), strict=True), headers={})


@_generator_endpoint("videos.create_resource")
async def create_resource(*, body: _CreateResourceBody) -> _generator_HandlerResponse[_CreateResourceResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.videos.Video").validate_json(_generator_json.dumps({"created_at": "2026-10-13T14:00:00Z", "description": "An introductory lesson", "duration_seconds": None, "id": "550e8400-e29b-41d4-a716-446655440000", "publication_status": "DRAFT", "published_at": None, "size_bytes": None, "status": "CREATED", "thumbnail": {"source": "NONE", "status": "PENDING", "url": None}, "title": "Introduction to Faith", "updated_at": "2026-10-13T14:00:00Z"}), strict=True), headers={"Location": "/v1/videos/550e8400-e29b-41d4-a716-446655440000"})


@_generator_endpoint("videos.delete_resource")
async def delete_resource(*, id: _generator_UUID) -> _generator_HandlerResponse[_DeleteResourceResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.videos.VideoDeletion").validate_json(_generator_json.dumps({"status": "DELETING", "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})


@_generator_endpoint("videos.get_resource")
async def get_resource(*, id: _generator_UUID) -> _generator_HandlerResponse[_GetResourceResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.videos.Video").validate_json(_generator_json.dumps({"created_at": "2026-10-13T14:00:00Z", "description": "An introductory lesson", "duration_seconds": 1475.5, "id": "550e8400-e29b-41d4-a716-446655440000", "publication_status": "DRAFT", "published_at": None, "size_bytes": 524288000, "status": "READY", "thumbnail": {"source": "GENERATED", "status": "READY", "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/generated.jpg"}, "title": "Introduction to Faith", "updated_at": "2026-10-13T14:05:00Z"}), strict=True), headers={})


@_generator_endpoint("videos.update_resource")
async def update_resource(*, id: _generator_UUID, body: _UpdateResourceBody) -> _generator_HandlerResponse[_UpdateResourceResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.videos.Video").validate_json(_generator_json.dumps({"created_at": "2026-10-13T14:00:00Z", "description": "An introductory lesson", "duration_seconds": 1475.5, "id": "550e8400-e29b-41d4-a716-446655440000", "publication_status": "DRAFT", "published_at": None, "size_bytes": 524288000, "status": "READY", "thumbnail": {"source": "GENERATED", "status": "READY", "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/generated.jpg"}, "title": "Introduction to Faith", "updated_at": "2026-10-13T14:05:00Z"}), strict=True), headers={})


@_generator_endpoint("videos.retry_processing")
async def retry_processing(*, id: _generator_UUID) -> _generator_HandlerResponse[_RetryProcessingResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.videos.VideoRetry").validate_json(_generator_json.dumps({"attempt": 2, "processing_job_id": "ac9afc7e-d6d1-4b5d-b0f2-fdb591862ea5", "status": "QUEUED", "video_id": "550e8400-e29b-41d4-a716-446655440000"}), strict=True), headers={})
