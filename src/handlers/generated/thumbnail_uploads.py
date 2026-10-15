# Generated; do not edit.
from typing import Annotated as _generator_Annotated

from fastapi import APIRouter as _generator_APIRouter
from fastapi import Body as _generator_Body
from fastapi import Path as _generator_Path
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.operations import (
    ThumbnailUploadsCompleteResourceIdParameter as _CompleteResourceIdParameter,
)
from src.schemas.generated.operations import (
    ThumbnailUploadsCreateResourceIdParameter as _CreateResourceIdParameter,
)
from src.schemas.generated.thumbnails import Thumbnail as _CompleteResourceResponse
from src.schemas.generated.thumbnails import ThumbnailUpload as _CreateResourceResponse
from src.schemas.generated.thumbnails import (
    ThumbnailUploadCreate as _CreateResourceBody,
)
from src.schemas.generated.uploads import UploadComplete as _CompleteResourceBody

router = _generator_APIRouter(prefix="/v1/videos")


@router.post(
    "/{id}/thumbnail/complete-upload",
    response_model=_CompleteResourceResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("thumbnail_uploads.complete_resource")
async def complete_resource(
    *,
    id: _generator_Annotated[
        _CompleteResourceIdParameter, _generator_Path(alias="id", description="Video ID.")
    ],
    body: _generator_Annotated[_CompleteResourceBody, _generator_Body()],
) -> _CompleteResourceResponse:
    return _generator_TypeAdapter(_CompleteResourceResponse).validate_python(
        {
            "thumbnail": {
                "source": "CUSTOM",
                "status": "READY",
                "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        }
    )


@router.post(
    "/{id}/thumbnail/upload-url",
    response_model=_CreateResourceResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("thumbnail_uploads.create_resource")
async def create_resource(
    *,
    id: _generator_Annotated[
        _CreateResourceIdParameter, _generator_Path(alias="id", description="Video ID.")
    ],
    body: _generator_Annotated[_CreateResourceBody, _generator_Body()],
) -> _CreateResourceResponse:
    return _generator_TypeAdapter(_CreateResourceResponse).validate_python(
        {
            "upload": {
                "expires_at": "2026-10-13T14:15:00Z",
                "headers": {"Content-Type": "image/jpeg"},
                "method": "PUT",
                "upload_id": "50fd0382-794f-4c9b-9a12-60e92a89e008",
                "url": "https://uploads.example.com/thumbnail.jpg?signature=example",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        }
    )
