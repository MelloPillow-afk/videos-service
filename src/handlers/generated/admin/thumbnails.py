# Generated; do not edit.
# fmt: off
from typing import Annotated as _generator_Annotated

from fastapi import APIRouter as _generator_APIRouter
from fastapi import Body as _generator_Body
from fastapi import Depends as _generator_Depends
from fastapi import Path as _generator_Path
from fastapi import Response as _generator_Response
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.authentication import (
    require_authentication as _generator_require_authentication,
)
from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.jobs import Job as _CompleteUploadResponse
from src.schemas.generated.operations import (
    AdminThumbnailsCompleteUploadIdParameter as _CompleteUploadIdParameter,
)
from src.schemas.generated.operations import (
    AdminThumbnailsDeleteThumbnailIdParameter as _DeleteThumbnailIdParameter,
)
from src.schemas.generated.operations import (
    AdminThumbnailsUploadUrlIdParameter as _UploadUrlIdParameter,
)
from src.schemas.generated.thumbnails import Thumbnail as _DeleteThumbnailResponse
from src.schemas.generated.thumbnails import ThumbnailUpload as _UploadUrlResponse
from src.schemas.generated.thumbnails import ThumbnailUploadCreate as _UploadUrlBody
from src.schemas.generated.uploads import UploadComplete as _CompleteUploadBody

router = _generator_APIRouter(prefix="/v1/admin/videos")


@router.delete(
    "/{id}/thumbnails",
    response_model=_DeleteThumbnailResponse,
    status_code=200,
    response_model_exclude_unset=True,
    dependencies=[_generator_Depends(_generator_require_authentication)],
)
@_generator_select_endpoint("admin.thumbnails.delete_thumbnail")
async def delete_thumbnail(
    *,
    id: _generator_Annotated[
        _DeleteThumbnailIdParameter,
        _generator_Path(alias="id", description="Video ID."),
    ],
) -> _DeleteThumbnailResponse:
    return _generator_TypeAdapter(_DeleteThumbnailResponse).validate_python(
        {
            "thumbnail": {
                "sizes": {
                    "lg": {
                        "height": 540,
                        "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/50fd0382-794f-4c9b-9a12-60e92a89e008/lg.jpg",
                        "width": 960,
                    },
                    "md": {
                        "height": 360,
                        "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/50fd0382-794f-4c9b-9a12-60e92a89e008/md.jpg",
                        "width": 640,
                    },
                    "sm": {
                        "height": 180,
                        "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/50fd0382-794f-4c9b-9a12-60e92a89e008/sm.jpg",
                        "width": 320,
                    },
                    "xl": {
                        "height": 720,
                        "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/50fd0382-794f-4c9b-9a12-60e92a89e008/xl.jpg",
                        "width": 1280,
                    },
                    "xs": {
                        "height": 90,
                        "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/50fd0382-794f-4c9b-9a12-60e92a89e008/xs.jpg",
                        "width": 160,
                    },
                },
                "source": "CUSTOM",
                "status": "READY",
                "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/50fd0382-794f-4c9b-9a12-60e92a89e008/xl.jpg",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
    )


@router.post(
    "/{id}/thumbnails:complete-upload",
    response_model=_CompleteUploadResponse,
    status_code=202,
    response_model_exclude_unset=True,
    dependencies=[_generator_Depends(_generator_require_authentication)],
)
@_generator_select_endpoint("admin.thumbnails.complete_upload")
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
    "/{id}/thumbnails:upload-url",
    response_model=_UploadUrlResponse,
    status_code=200,
    response_model_exclude_unset=True,
    dependencies=[_generator_Depends(_generator_require_authentication)],
)
@_generator_select_endpoint("admin.thumbnails.upload_url")
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
            "upload": {
                "expires_at": "2026-10-13T14:15:00Z",
                "headers": {"Content-Type": "image/jpeg"},
                "method": "PUT",
                "upload_id": "50fd0382-794f-4c9b-9a12-60e92a89e008",
                "url": "https://uploads.example.com/thumbnail.jpg?signature=example",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
    )
