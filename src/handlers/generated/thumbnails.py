# Generated; do not edit.
from typing import Annotated as _generator_Annotated

from fastapi import APIRouter as _generator_APIRouter
from fastapi import Path as _generator_Path
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.operations import (
    ThumbnailsDeleteResourceIdParameter as _DeleteResourceIdParameter,
)
from src.schemas.generated.thumbnails import Thumbnail as _DeleteResourceResponse

router = _generator_APIRouter(prefix="/v1/videos")


@router.delete(
    "/{id}/thumbnail",
    response_model=_DeleteResourceResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("thumbnails.delete_resource")
async def delete_resource(
    *,
    id: _generator_Annotated[
        _DeleteResourceIdParameter, _generator_Path(alias="id", description="Video ID.")
    ],
) -> _DeleteResourceResponse:
    return _generator_TypeAdapter(_DeleteResourceResponse).validate_python(
        {
            "thumbnail": {
                "source": "CUSTOM",
                "status": "READY",
                "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        }
    )
