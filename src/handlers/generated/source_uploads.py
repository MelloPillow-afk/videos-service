# Generated; do not edit.
from typing import Annotated as _generator_Annotated

from fastapi import APIRouter as _generator_APIRouter
from fastapi import Body as _generator_Body
from fastapi import Path as _generator_Path
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.operations import (
    SourceUploadsCompleteResourceIdParameter as _CompleteResourceIdParameter,
)
from src.schemas.generated.operations import (
    SourceUploadsCreateResourceIdParameter as _CreateResourceIdParameter,
)
from src.schemas.generated.uploads import SourceUpload as _CreateResourceResponse
from src.schemas.generated.uploads import SourceUploadCreate as _CreateResourceBody
from src.schemas.generated.uploads import (
    SourceUploadProcessing as _CompleteResourceResponse,
)
from src.schemas.generated.uploads import UploadComplete as _CompleteResourceBody

router = _generator_APIRouter(prefix="/v1/videos")


@router.post(
    "/{id}/complete-upload",
    response_model=_CompleteResourceResponse,
    status_code=202,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("source_uploads.complete_resource")
async def complete_resource(
    *,
    id: _generator_Annotated[
        _CompleteResourceIdParameter, _generator_Path(alias="id", description="Video ID.")
    ],
    body: _generator_Annotated[_CompleteResourceBody, _generator_Body()],
) -> _CompleteResourceResponse:
    return _generator_TypeAdapter(_CompleteResourceResponse).validate_python(
        {
            "processing_job_id": "e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0",
            "status": "QUEUED",
            "thumbnail_status": "PENDING",
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        }
    )


@router.post(
    "/{id}/upload-url",
    response_model=_CreateResourceResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("source_uploads.create_resource")
async def create_resource(
    *,
    id: _generator_Annotated[
        _CreateResourceIdParameter, _generator_Path(alias="id", description="Video ID.")
    ],
    body: _generator_Annotated[_CreateResourceBody, _generator_Body()],
) -> _CreateResourceResponse:
    return _generator_TypeAdapter(_CreateResourceResponse).validate_python(
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
        }
    )
