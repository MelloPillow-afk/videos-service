# Generated; do not edit.
# fmt: off
from typing import Annotated as _generator_Annotated

from fastapi import APIRouter as _generator_APIRouter
from fastapi import Body as _generator_Body
from fastapi import Path as _generator_Path
from fastapi import Query as _generator_Query
from fastapi import Response as _generator_Response
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.operations import (
    VideosCompleteUploadIdParameter as _CompleteUploadIdParameter,
)
from src.schemas.generated.operations import (
    VideosDeleteVideoIdParameter as _DeleteVideoIdParameter,
)
from src.schemas.generated.operations import (
    VideosGetVideoIdParameter as _GetVideoIdParameter,
)
from src.schemas.generated.operations import (
    VideosListVideosCursorParameter as _ListVideosCursorParameter,
)
from src.schemas.generated.operations import (
    VideosListVideosLimitParameter as _ListVideosLimitParameter,
)
from src.schemas.generated.operations import (
    VideosListVideosSearchParameter as _ListVideosSearchParameter,
)
from src.schemas.generated.operations import (
    VideosRetryProcessingIdParameter as _RetryProcessingIdParameter,
)
from src.schemas.generated.operations import (
    VideosUpdateVideoIdParameter as _UpdateVideoIdParameter,
)
from src.schemas.generated.operations import (
    VideosUploadUrlIdParameter as _UploadUrlIdParameter,
)
from src.schemas.generated.uploads import SourceUpload as _UploadUrlResponse
from src.schemas.generated.uploads import SourceUploadCreate as _UploadUrlBody
from src.schemas.generated.uploads import (
    SourceUploadProcessing as _CompleteUploadResponse,
)
from src.schemas.generated.uploads import UploadComplete as _CompleteUploadBody
from src.schemas.generated.videos import (
    PublicationStatus as _ListVideosPublicationStatusParameter,
)
from src.schemas.generated.videos import Video as _CreateVideoResponse
from src.schemas.generated.videos import Video as _GetVideoResponse
from src.schemas.generated.videos import Video as _UpdateVideoResponse
from src.schemas.generated.videos import VideoCreate as _CreateVideoBody
from src.schemas.generated.videos import VideoDeletion as _DeleteVideoResponse
from src.schemas.generated.videos import VideoRetry as _RetryProcessingResponse
from src.schemas.generated.videos import Videos as _ListVideosResponse
from src.schemas.generated.videos import VideoStatus as _ListVideosStatusParameter
from src.schemas.generated.videos import VideoUpdate as _UpdateVideoBody

router = _generator_APIRouter(prefix="/v1")


@router.get(
    "/videos",
    response_model=_ListVideosResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.list_videos")
async def list_videos(
    *,
    cursor: _generator_Annotated[
        _ListVideosCursorParameter | None,
        _generator_Query(alias="cursor", description="Token from the previous page."),
    ] = None,
    limit: _generator_Annotated[
        _ListVideosLimitParameter,
        _generator_Query(alias="limit", description="Maximum number of videos to return."),
    ] = 20,
    publication_status: _generator_Annotated[
        _ListVideosPublicationStatusParameter | None,
        _generator_Query(
            alias="publication_status",
            description="Filter by publication status.",
        ),
    ] = None,
    search: _generator_Annotated[
        _ListVideosSearchParameter | None,
        _generator_Query(alias="search", description="Search video titles."),
    ] = None,
    status: _generator_Annotated[
        _ListVideosStatusParameter | None,
        _generator_Query(alias="status", description="Filter by video status."),
    ] = None,
) -> _ListVideosResponse:
    return _generator_TypeAdapter(_ListVideosResponse).validate_python(
        {
            "data": [
                {
                    "created_at": "2026-10-13T14:00:00Z",
                    "description": "An introductory lesson",
                    "duration_seconds": 147.5,
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "publication_status": "PUBLISHED",
                    "published_at": "2026-10-13T15:00:00Z",
                    "size_bytes": 52428800,
                    "status": "READY",
                    "thumbnail": {
                        "source": "CUSTOM",
                        "status": "READY",
                        "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg",
                    },
                    "title": "Introduction to Faith",
                    "updated_at": "2026-10-13T15:00:00Z",
                },
            ],
            "pagination": {"has_more": True, "next_page_token": "example_next_page_token"},
        },
    )


@router.post(
    "/videos",
    response_model=_CreateVideoResponse,
    status_code=201,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.create_video")
async def create_video(
    *,
    body: _generator_Annotated[_CreateVideoBody, _generator_Body()],
    response: _generator_Response,
) -> _CreateVideoResponse:
    response.headers["Location"] = "/v1/videos/550e8400-e29b-41d4-a716-446655440000"
    return _generator_TypeAdapter(_CreateVideoResponse).validate_python(
        {
            "created_at": "2026-10-13T14:00:00Z",
            "description": "An introductory lesson",
            "duration_seconds": None,
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "publication_status": "DRAFT",
            "published_at": None,
            "size_bytes": None,
            "status": "CREATED",
            "thumbnail": {"source": "NONE", "status": "PENDING", "url": None},
            "title": "Introduction to Faith",
            "updated_at": "2026-10-13T14:00:00Z",
        },
    )


@router.delete(
    "/videos/{id}",
    response_model=_DeleteVideoResponse,
    status_code=202,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.delete_video")
async def delete_video(
    *,
    id: _generator_Annotated[
        _DeleteVideoIdParameter,
        _generator_Path(alias="id", description="Video ID."),
    ],
) -> _DeleteVideoResponse:
    return _generator_TypeAdapter(_DeleteVideoResponse).validate_python(
        {"status": "DELETING", "video_id": "550e8400-e29b-41d4-a716-446655440000"},
    )


@router.get(
    "/videos/{id}",
    response_model=_GetVideoResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.get_video")
async def get_video(
    *,
    id: _generator_Annotated[
        _GetVideoIdParameter,
        _generator_Path(alias="id", description="Video ID."),
    ],
) -> _GetVideoResponse:
    return _generator_TypeAdapter(_GetVideoResponse).validate_python(
        {
            "created_at": "2026-10-13T14:00:00Z",
            "description": "An introductory lesson",
            "duration_seconds": None,
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "publication_status": "DRAFT",
            "published_at": None,
            "size_bytes": None,
            "status": "CREATED",
            "thumbnail": {"source": "NONE", "status": "PENDING", "url": None},
            "title": "Introduction to Faith",
            "updated_at": "2026-10-13T14:00:00Z",
        },
    )


@router.patch(
    "/videos/{id}",
    response_model=_UpdateVideoResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.update_video")
async def update_video(
    *,
    id: _generator_Annotated[
        _UpdateVideoIdParameter,
        _generator_Path(alias="id", description="Video ID."),
    ],
    body: _generator_Annotated[_UpdateVideoBody, _generator_Body()],
) -> _UpdateVideoResponse:
    return _generator_TypeAdapter(_UpdateVideoResponse).validate_python(
        {
            "created_at": "2026-10-13T14:00:00Z",
            "description": "An introductory lesson",
            "duration_seconds": None,
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "publication_status": "DRAFT",
            "published_at": None,
            "size_bytes": None,
            "status": "CREATED",
            "thumbnail": {"source": "NONE", "status": "PENDING", "url": None},
            "title": "Introduction to Faith",
            "updated_at": "2026-10-13T14:00:00Z",
        },
    )


@router.post(
    "/videos/{id}:complete-upload",
    response_model=_CompleteUploadResponse,
    status_code=202,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.complete_upload")
async def complete_upload(
    *,
    id: _generator_Annotated[
        _CompleteUploadIdParameter,
        _generator_Path(alias="id", description="Video ID."),
    ],
    body: _generator_Annotated[_CompleteUploadBody, _generator_Body()],
) -> _CompleteUploadResponse:
    return _generator_TypeAdapter(_CompleteUploadResponse).validate_python(
        {
            "processing_job_id": "e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0",
            "status": "QUEUED",
            "thumbnail_status": "PENDING",
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
    )


@router.post(
    "/videos/{id}:retry",
    response_model=_RetryProcessingResponse,
    status_code=202,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.retry_processing")
async def retry_processing(
    *,
    id: _generator_Annotated[
        _RetryProcessingIdParameter,
        _generator_Path(alias="id", description="Video ID."),
    ],
) -> _RetryProcessingResponse:
    return _generator_TypeAdapter(_RetryProcessingResponse).validate_python(
        {
            "attempt": 2,
            "processing_job_id": "ac9afc7e-d6d1-4b5d-b0f2-fdb591862ea5",
            "status": "QUEUED",
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
    )


@router.post(
    "/videos/{id}:upload-url",
    response_model=_UploadUrlResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.upload_url")
async def upload_url(
    *,
    id: _generator_Annotated[
        _UploadUrlIdParameter,
        _generator_Path(alias="id", description="Video ID."),
    ],
    body: _generator_Annotated[_UploadUrlBody, _generator_Body()],
) -> _UploadUrlResponse:
    return _generator_TypeAdapter(_UploadUrlResponse).validate_python(
        {
            "status": "UPLOADING",
            "upload": {
                "expires_at": "2026-10-13T14:15:00Z",
                "headers": {"Content-Type": "video/mp4", "If-None-Match": "*"},
                "method": "PUT",
                "upload_id": "04d1790f-f941-4ba6-8d97-0e6830ca4394",
                "url": "https://uploads.example.com/source.mp4?signature=example",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
    )
