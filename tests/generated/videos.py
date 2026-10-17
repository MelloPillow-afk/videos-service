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
        "expected_status": 200,
        "method": "GET",
        "operation_id": "videos.list_videos",
        "parameters": [
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
                "attribute": "page_token",
                "description": "The next_page_token from the previous page.",
                "in": "query",
                "model": "src.schemas.generated.operations.VideosListVideosPageTokenParameter",
                "name": "page_token",
                "required": False,
                "type": "string",
            },
        ],
        "path": "/v1/videos",
        "path_params": {},
        "query": {
            "limit": 20,
            "page_token": "eyJ0IjoiMjAyNi0xMC0xNFQwOTowMDowMC4wMDAwMDArMDA6MDAiLCJpZCI6IjNmMmI4YzFlLTdkNGEtNGU2Yi05YzBmLTVhMWQyZTNiNGM1ZCJ9",
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
