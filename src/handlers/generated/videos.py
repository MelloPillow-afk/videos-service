# Generated; do not edit.
# fmt: off
from typing import Annotated as _generator_Annotated

from fastapi import APIRouter as _generator_APIRouter
from fastapi import Depends as _generator_Depends
from fastapi import Query as _generator_Query
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.authentication import (
    optional_authentication as _generator_optional_authentication,
)
from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.operations import (
    VideosListVideosLimitParameter as _ListVideosLimitParameter,
)
from src.schemas.generated.operations import (
    VideosListVideosPageTokenParameter as _ListVideosPageTokenParameter,
)
from src.schemas.generated.videos import Videos as _ListVideosResponse

router = _generator_APIRouter(prefix="/v1")


@router.get(
    "/videos",
    response_model=_ListVideosResponse,
    status_code=200,
    response_model_exclude_unset=True,
    dependencies=[_generator_Depends(_generator_optional_authentication)],
)
@_generator_select_endpoint("videos.list_videos")
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
) -> _ListVideosResponse:
    return _generator_TypeAdapter(_ListVideosResponse).validate_python(
        {
            "data": [
                {
                    "description": "An introductory lesson",
                    "duration_seconds": 1475.5,
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "published_at": "2026-10-13T15:00:00Z",
                    "thumbnail": {
                        "source": "CUSTOM",
                        "status": "READY",
                        "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg",
                    },
                    "title": "Introduction to Faith",
                },
            ],
            "pagination": {"has_more": False, "next_page_token": None},
        },
    )
