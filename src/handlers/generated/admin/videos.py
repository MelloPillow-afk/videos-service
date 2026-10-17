# Generated; do not edit.
# fmt: off
from typing import Annotated as _generator_Annotated

from fastapi import APIRouter as _generator_APIRouter
from fastapi import Body as _generator_Body
from fastapi import Depends as _generator_Depends
from fastapi import Path as _generator_Path
from fastapi import Query as _generator_Query
from fastapi import Response as _generator_Response
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.authentication import (
    require_authentication as _generator_require_authentication,
)
from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.jobs import Job as _CompleteUploadResponse
from src.schemas.generated.operations import (
    AdminVideosCompleteUploadIdParameter as _CompleteUploadIdParameter,
)
from src.schemas.generated.operations import (
    AdminVideosDeleteVideoIdParameter as _DeleteVideoIdParameter,
)
from src.schemas.generated.operations import (
    AdminVideosGetVideoIdParameter as _GetVideoIdParameter,
)
from src.schemas.generated.operations import (
    AdminVideosListVideosLimitParameter as _ListVideosLimitParameter,
)
from src.schemas.generated.operations import (
    AdminVideosListVideosPageTokenParameter as _ListVideosPageTokenParameter,
)
from src.schemas.generated.operations import (
    AdminVideosUpdateVideoIdParameter as _UpdateVideoIdParameter,
)
from src.schemas.generated.operations import (
    AdminVideosUploadUrlIdParameter as _UploadUrlIdParameter,
)
from src.schemas.generated.uploads import SourceUpload as _UploadUrlResponse
from src.schemas.generated.uploads import SourceUploadCreate as _UploadUrlBody
from src.schemas.generated.uploads import UploadComplete as _CompleteUploadBody
from src.schemas.generated.videos import AdminVideo as _CreateVideoResponse
from src.schemas.generated.videos import AdminVideo as _GetVideoResponse
from src.schemas.generated.videos import AdminVideo as _UpdateVideoResponse
from src.schemas.generated.videos import AdminVideoCreate as _CreateVideoBody
from src.schemas.generated.videos import AdminVideos as _ListVideosResponse
from src.schemas.generated.videos import AdminVideoUpdate as _UpdateVideoBody
from src.schemas.generated.videos import (
    PublicationStatus as _ListVideosPublicationStatusParameter,
)

router = _generator_APIRouter(prefix="/v1/admin")


@router.get(
    "/videos",
    response_model=_ListVideosResponse,
    status_code=200,
    response_model_exclude_unset=True,
    dependencies=[_generator_Depends(_generator_require_authentication)],
)
@_generator_select_endpoint("admin.videos.list_videos")
async def list_videos(
    *,
    limit: _generator_Annotated[
        _ListVideosLimitParameter,
        _generator_Query(alias="limit", description="Maximum number of videos to return."),
    ] = 20,
    page_token: _generator_Annotated[
        _ListVideosPageTokenParameter | None,
        _generator_Query(
            alias="page_token",
            description="The next_page_token from the previous page.",
        ),
    ] = None,
    publication_status: _generator_Annotated[
        _ListVideosPublicationStatusParameter | None,
        _generator_Query(
            alias="publication_status",
            description="Filter by publication status.",
        ),
    ] = None,
) -> _ListVideosResponse:
    return _generator_TypeAdapter(_ListVideosResponse).validate_python(
        {
            "data": [
                {
                    "created_at": "2026-10-13T14:00:00Z",
                    "description": "An introductory lesson",
                    "duration_seconds": None,
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "latest_job_id": None,
                    "publication_status": "DRAFT",
                    "published_at": None,
                    "size_bytes": None,
                    "status": "CREATED",
                    "thumbnail": {"source": "NONE", "status": "PENDING", "url": None},
                    "title": "Introduction to Faith",
                    "updated_at": "2026-10-13T14:00:00Z",
                },
            ],
            "pagination": {"has_more": False, "next_page_token": None},
        },
    )


@router.post(
    "/videos",
    response_model=_CreateVideoResponse,
    status_code=201,
    response_model_exclude_unset=True,
    dependencies=[_generator_Depends(_generator_require_authentication)],
)
@_generator_select_endpoint("admin.videos.create_video")
async def create_video(
    *,
    body: _generator_Annotated[_CreateVideoBody, _generator_Body()],
    response: _generator_Response,
) -> _CreateVideoResponse:
    response.headers["Location"] = "/v1/admin/videos/550e8400-e29b-41d4-a716-446655440000"
    return _generator_TypeAdapter(_CreateVideoResponse).validate_python(
        {
            "created_at": "2026-10-13T14:00:00Z",
            "description": "An introductory lesson",
            "duration_seconds": None,
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "latest_job_id": None,
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
    response_model=None,
    status_code=204,
    response_model_exclude_unset=True,
    dependencies=[_generator_Depends(_generator_require_authentication)],
)
@_generator_select_endpoint("admin.videos.delete_video")
async def delete_video(
    *,
    id: _generator_Annotated[
        _DeleteVideoIdParameter,
        _generator_Path(alias="id", description="Video ID."),
    ],
) -> None:
    return None


@router.get(
    "/videos/{id}",
    response_model=_GetVideoResponse,
    status_code=200,
    response_model_exclude_unset=True,
    dependencies=[_generator_Depends(_generator_require_authentication)],
)
@_generator_select_endpoint("admin.videos.get_video")
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
            "latest_job_id": None,
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
    dependencies=[_generator_Depends(_generator_require_authentication)],
)
@_generator_select_endpoint("admin.videos.update_video")
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
            "latest_job_id": None,
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
    dependencies=[_generator_Depends(_generator_require_authentication)],
)
@_generator_select_endpoint("admin.videos.complete_upload")
async def complete_upload(
    *,
    id: _generator_Annotated[
        _CompleteUploadIdParameter,
        _generator_Path(alias="id", description="Video ID."),
    ],
    body: _generator_Annotated[_CompleteUploadBody, _generator_Body()],
    response: _generator_Response,
) -> _CompleteUploadResponse:
    response.headers["Location"] = "/v1/jobs/e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0"
    return _generator_TypeAdapter(_CompleteUploadResponse).validate_python(
        {
            "id": "e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0",
            "message": None,
            "status": "QUEUED",
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
    )


@router.post(
    "/videos/{id}:upload-url",
    response_model=_UploadUrlResponse,
    status_code=200,
    response_model_exclude_unset=True,
    dependencies=[_generator_Depends(_generator_require_authentication)],
)
@_generator_select_endpoint("admin.videos.upload_url")
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
                "headers": {"Content-Type": "video/mp4"},
                "method": "PUT",
                "upload_id": "04d1790f-f941-4ba6-8d97-0e6830ca4394",
                "url": "https://uploads.example.com/source.mp4?signature=example",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
    )
