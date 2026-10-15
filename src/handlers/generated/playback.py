# Generated; do not edit.
from typing import Annotated as _generator_Annotated

from fastapi import APIRouter as _generator_APIRouter
from fastapi import Path as _generator_Path
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.operations import (
    PlaybackGetResourceIdParameter as _GetResourceIdParameter,
)
from src.schemas.generated.playback import Playback as _GetResourceResponse

router = _generator_APIRouter(prefix="/v1/videos")


@router.get(
    "/{id}/playback",
    response_model=_GetResourceResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("playback.get_resource")
async def get_resource(
    *,
    id: _generator_Annotated[
        _GetResourceIdParameter, _generator_Path(alias="id", description="Video ID.")
    ],
) -> _GetResourceResponse:
    return _generator_TypeAdapter(_GetResourceResponse).validate_python(
        {
            "playback": {
                "type": "hls",
                "url": "https://media.example.com/videos/intro/hls/master.m3u8",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        }
    )
