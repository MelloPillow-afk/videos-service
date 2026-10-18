# Generated; do not edit.
# fmt: off
from typing import Any

import pytest
from httpx import AsyncClient

from ._support import APICase

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_CASES: dict[str, dict[str, Any]] = {
    "videos.get_video": {
        "authentication": "optional",
        "body": None,
        "body_model": None,
        "expected_body": {
            "description": "An introductory lesson",
            "duration_seconds": 1475.5,
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "published_at": "2026-10-13T15:00:00Z",
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
            "title": "Introduction to Faith",
        },
        "expected_status": 200,
        "method": "GET",
        "operation_id": "videos.get_video",
        "parameters": [
            {
                "attribute": "id",
                "description": "Video ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.VideosGetVideoIdParameter",
                "name": "id",
                "required": True,
                "type": "string",
            },
        ],
        "path": "/v1/videos/{id}",
        "path_params": {"id": "550e8400-e29b-41d4-a716-446655440000"},
        "query": {},
        "response_model": "src.schemas.generated.videos.Video",
    },
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
    _CASES["videos.get_video"],
)
@pytest.mark.usefixtures("arrange_videos_get_video")
async def test_get_video_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["videos.get_video"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_videos_get_video")
async def test_get_video_422_path_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


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
