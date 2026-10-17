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
    VideosListVideosCursorParameter as _ListVideosCursorParameter,
)
from src.schemas.generated.operations import (
    VideosListVideosLimitParameter as _ListVideosLimitParameter,
)
from src.schemas.generated.operations import (
    VideosListVideosSearchParameter as _ListVideosSearchParameter,
)
from src.schemas.generated.videos import (
    PublicationStatus as _ListVideosPublicationStatusParameter,
)
from src.schemas.generated.videos import Videos as _ListVideosResponse
from src.schemas.generated.videos import VideoStatus as _ListVideosStatusParameter

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
                    "duration_seconds": 1475.5,
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "latest_job_id": "e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0",
                    "publication_status": "PUBLISHED",
                    "published_at": "2026-10-13T15:00:00Z",
                    "size_bytes": 524288000,
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
