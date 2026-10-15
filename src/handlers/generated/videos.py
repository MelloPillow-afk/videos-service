# Generated; do not edit.
from typing import Annotated as _generator_Annotated

from fastapi import APIRouter as _generator_APIRouter
from fastapi import Body as _generator_Body
from fastapi import Path as _generator_Path
from fastapi import Query as _generator_Query
from fastapi import Response as _generator_Response
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.operations import (
    VideosDeleteResourceIdParameter as _DeleteResourceIdParameter,
)
from src.schemas.generated.operations import (
    VideosGetCollectionCursorParameter as _GetCollectionCursorParameter,
)
from src.schemas.generated.operations import (
    VideosGetCollectionLimitParameter as _GetCollectionLimitParameter,
)
from src.schemas.generated.operations import (
    VideosGetCollectionSearchParameter as _GetCollectionSearchParameter,
)
from src.schemas.generated.operations import (
    VideosGetResourceIdParameter as _GetResourceIdParameter,
)
from src.schemas.generated.operations import (
    VideosRetryProcessingIdParameter as _RetryProcessingIdParameter,
)
from src.schemas.generated.operations import (
    VideosUpdateResourceIdParameter as _UpdateResourceIdParameter,
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

router = _generator_APIRouter(prefix="/v1")


@router.get(
    "/videos",
    response_model=_GetCollectionResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.get_collection")
async def get_collection(
    *,
    cursor: _generator_Annotated[
        _GetCollectionCursorParameter | None,
        _generator_Query(alias="cursor", description="Token from the previous page."),
    ] = None,
    limit: _generator_Annotated[
        _GetCollectionLimitParameter,
        _generator_Query(alias="limit", description="Maximum number of videos to return."),
    ] = 20,
    publication_status: _generator_Annotated[
        _GetCollectionPublicationStatusParameter | None,
        _generator_Query(alias="publication_status", description="Filter by publication status."),
    ] = None,
    search: _generator_Annotated[
        _GetCollectionSearchParameter | None,
        _generator_Query(alias="search", description="Search video titles."),
    ] = None,
    status: _generator_Annotated[
        _GetCollectionStatusParameter | None,
        _generator_Query(alias="status", description="Filter by video status."),
    ] = None,
) -> _GetCollectionResponse:
    return _generator_TypeAdapter(_GetCollectionResponse).validate_python(
        {
            "data": [
                {
                    "created_at": "2026-10-13T14:00:00Z",
                    "description": "An introductory lesson",
                    "duration_seconds": 1475.5,
                    "id": "550e8400-e29b-41d4-a716-446655440000",
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
                }
            ],
            "pagination": {"has_more": True, "next_page_token": "example_next_page_token"},
        }
    )


@router.post(
    "/videos",
    response_model=_CreateResourceResponse,
    status_code=201,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.create_resource")
async def create_resource(
    *,
    body: _generator_Annotated[_CreateResourceBody, _generator_Body()],
    response: _generator_Response,
) -> _CreateResourceResponse:
    response.headers["Location"] = "/v1/videos/550e8400-e29b-41d4-a716-446655440000"
    return _generator_TypeAdapter(_CreateResourceResponse).validate_python(
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
        }
    )


@router.delete(
    "/videos/{id}",
    response_model=_DeleteResourceResponse,
    status_code=202,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.delete_resource")
async def delete_resource(
    *,
    id: _generator_Annotated[
        _DeleteResourceIdParameter, _generator_Path(alias="id", description="Video ID.")
    ],
) -> _DeleteResourceResponse:
    return _generator_TypeAdapter(_DeleteResourceResponse).validate_python(
        {"status": "DELETING", "video_id": "550e8400-e29b-41d4-a716-446655440000"}
    )


@router.get(
    "/videos/{id}",
    response_model=_GetResourceResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.get_resource")
async def get_resource(
    *,
    id: _generator_Annotated[
        _GetResourceIdParameter, _generator_Path(alias="id", description="Video ID.")
    ],
) -> _GetResourceResponse:
    return _generator_TypeAdapter(_GetResourceResponse).validate_python(
        {
            "created_at": "2026-10-13T14:00:00Z",
            "description": "An introductory lesson",
            "duration_seconds": 1475.5,
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "publication_status": "DRAFT",
            "published_at": None,
            "size_bytes": 524288000,
            "status": "READY",
            "thumbnail": {
                "source": "GENERATED",
                "status": "READY",
                "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/generated.jpg",
            },
            "title": "Introduction to Faith",
            "updated_at": "2026-10-13T14:05:00Z",
        }
    )


@router.patch(
    "/videos/{id}",
    response_model=_UpdateResourceResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.update_resource")
async def update_resource(
    *,
    id: _generator_Annotated[
        _UpdateResourceIdParameter, _generator_Path(alias="id", description="Video ID.")
    ],
    body: _generator_Annotated[_UpdateResourceBody, _generator_Body()],
) -> _UpdateResourceResponse:
    return _generator_TypeAdapter(_UpdateResourceResponse).validate_python(
        {
            "created_at": "2026-10-13T14:00:00Z",
            "description": "An introductory lesson",
            "duration_seconds": 1475.5,
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "publication_status": "DRAFT",
            "published_at": None,
            "size_bytes": 524288000,
            "status": "READY",
            "thumbnail": {
                "source": "GENERATED",
                "status": "READY",
                "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/generated.jpg",
            },
            "title": "Introduction to Faith",
            "updated_at": "2026-10-13T14:05:00Z",
        }
    )


@router.post(
    "/videos/{id}/retry",
    response_model=_RetryProcessingResponse,
    status_code=202,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("videos.retry_processing")
async def retry_processing(
    *,
    id: _generator_Annotated[
        _RetryProcessingIdParameter, _generator_Path(alias="id", description="Video ID.")
    ],
) -> _RetryProcessingResponse:
    return _generator_TypeAdapter(_RetryProcessingResponse).validate_python(
        {
            "attempt": 2,
            "processing_job_id": "ac9afc7e-d6d1-4b5d-b0f2-fdb591862ea5",
            "status": "QUEUED",
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        }
    )
