# Generated; do not edit.
# fmt: off
from typing import Any

import pytest
from httpx import AsyncClient

from ._support import APICase

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_CASES: dict[str, dict[str, Any]] = {
    "videos.list_videos": {
        "authentication": "optional",
        "body": None,
        "body_model": None,
        "expected_body": {
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
        "expected_status": 200,
        "method": "GET",
        "operation_id": "videos.list_videos",
        "parameters": [
            {
                "attribute": "cursor",
                "description": "Token from the previous page.",
                "in": "query",
                "model": "src.schemas.generated.operations.VideosListVideosCursorParameter",
                "name": "cursor",
                "required": False,
                "type": "string",
            },
            {
                "attribute": "limit",
                "default": 20,
                "description": "Maximum number of videos to return.",
                "in": "query",
                "model": "src.schemas.generated.operations.VideosListVideosLimitParameter",
                "name": "limit",
                "required": False,
                "type": "integer",
            },
            {
                "attribute": "publication_status",
                "description": "Filter by publication status.",
                "in": "query",
                "model": "src.schemas.generated.videos.PublicationStatus",
                "name": "publication_status",
                "required": False,
                "type": "string",
            },
            {
                "attribute": "search",
                "description": "Search video titles.",
                "in": "query",
                "model": "src.schemas.generated.operations.VideosListVideosSearchParameter",
                "name": "search",
                "required": False,
                "type": "string",
            },
            {
                "attribute": "status",
                "description": "Filter by video status.",
                "in": "query",
                "model": "src.schemas.generated.videos.VideoStatus",
                "name": "status",
                "required": False,
                "type": "string",
            },
        ],
        "path": "/v1/videos",
        "path_params": {},
        "query": {
            "cursor": "example_next_page_token",
            "limit": 20,
            "publication_status": "DRAFT",
            "search": "faith",
            "status": "CREATED",
        },
        "response_model": "src.schemas.generated.videos.Videos",
    },
}


# GET


@pytest.mark.api_case(
    _CASES["videos.list_videos"],
)
@pytest.mark.usefixtures("arrange_videos_list_videos")
async def test_list_videos_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["videos.list_videos"], mutation={
        "error_types": ["less_than_equal", "greater_than_equal"],
        "in": "query",
        "name": "limit",
        "value": 101,
    },
)
@pytest.mark.usefixtures("arrange_videos_list_videos")
async def test_list_videos_422_query_limit_above_maximum(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["videos.list_videos"], mutation={
        "error_types": ["greater_than_equal", "less_than_equal"],
        "in": "query",
        "name": "limit",
        "value": 0,
    },
)
@pytest.mark.usefixtures("arrange_videos_list_videos")
async def test_list_videos_422_query_limit_below_minimum(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["videos.list_videos"], mutation={
        "error_types": ["int_parsing", "greater_than_equal", "less_than_equal"],
        "in": "query",
        "name": "limit",
        "value": "not-an-integer",
    },
)
@pytest.mark.usefixtures("arrange_videos_list_videos")
async def test_list_videos_422_query_limit_invalid_type(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["videos.list_videos"], mutation={
        "error_types": [
            "value_error",
            "literal_error",
            "greater_than_equal",
            "less_than_equal",
            "string_too_short",
            "string_too_long",
            "string_pattern_mismatch",
        ],
        "in": "query",
        "name": "publication_status",
        "value": "__invalid__",
    },
)
@pytest.mark.usefixtures("arrange_videos_list_videos")
async def test_list_videos_422_query_publication_status_outside_allowed_values(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["videos.list_videos"], mutation={
        "error_types": ["string_too_long"],
        "in": "query",
        "name": "search",
        "value": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    },
)
@pytest.mark.usefixtures("arrange_videos_list_videos")
async def test_list_videos_422_query_search_too_long(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["videos.list_videos"], mutation={
        "error_types": [
            "value_error",
            "literal_error",
            "greater_than_equal",
            "less_than_equal",
            "string_too_short",
            "string_too_long",
            "string_pattern_mismatch",
        ],
        "in": "query",
        "name": "status",
        "value": "__invalid__",
    },
)
@pytest.mark.usefixtures("arrange_videos_list_videos")
async def test_list_videos_422_query_status_outside_allowed_values(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()
