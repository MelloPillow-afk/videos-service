# Generated; do not edit.
# fmt: off
from typing import Any

import pytest
from httpx import AsyncClient

from ._support import APICase

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_CASES: dict[str, dict[str, Any]] = {
    "videos.create_video": {
        "body": {"description": "An introductory lesson", "title": "Introduction to Faith"},
        "body_model": {
            "attribute": "body",
            "model": "src.schemas.generated.videos.VideoCreate",
            "required": True,
            "source": "/private/tmp/videos-showcase-mel14/api-specs/schemas/videos/video_create.yaml#",
        },
        "expected_body": {
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
        },
        "expected_status": 201,
        "method": "POST",
        "operation_id": "videos.create_video",
        "parameters": [],
        "path": "/v1/videos",
        "path_params": {},
        "query": {},
        "response_model": "src.schemas.generated.videos.Video",
    },
    "videos.get_video": {
        "body": None,
        "body_model": None,
        "expected_body": {
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
        "body": None,
        "body_model": None,
        "expected_body": {
            "data": [
                {
                    "created_at": "2026-10-13T14:00:00Z",
                    "description": "An introductory lesson",
                    "duration_seconds": 147.5,
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "publication_status": "PUBLISHED",
                    "published_at": "2026-10-13T15:00:00Z",
                    "size_bytes": 52428800,
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
                "description": "Opaque continuation token bound to the original filters, search, page size,\nand visibility.\n",
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
    "videos.update_video": {
        "body": {
            "description": "An introductory lesson",
            "publication_status": "DRAFT",
            "title": "Introduction to Faith",
        },
        "body_model": {
            "attribute": "body",
            "model": "src.schemas.generated.videos.VideoUpdate",
            "required": True,
            "source": "/private/tmp/videos-showcase-mel14/api-specs/schemas/videos/video_update.yaml#",
        },
        "expected_body": {
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
        },
        "expected_status": 200,
        "method": "PATCH",
        "operation_id": "videos.update_video",
        "parameters": [
            {
                "attribute": "id",
                "description": "Video ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.VideosUpdateVideoIdParameter",
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
    "videos.upload_url": {
        "body": {"content_type": "video/mp4", "file_name": "introduction.mp4", "size_bytes": 52428800},
        "body_model": {
            "attribute": "body",
            "model": "src.schemas.generated.uploads.SourceUploadCreate",
            "required": True,
            "source": "/private/tmp/videos-showcase-mel14/api-specs/schemas/uploads/source_upload_create.yaml#",
        },
        "expected_body": {
            "status": "UPLOADING",
            "upload": {
                "expires_at": "2026-10-13T14:15:00Z",
                "headers": {"Content-Type": "video/mp4", "If-None-Match": "*"},
                "method": "PUT",
                "upload_id": "04d1790f-f941-4ba6-8d97-0e6830ca4394",
                "url": "https://uploads.example.com/source.mp4?signature=example",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        "expected_status": 200,
        "method": "POST",
        "operation_id": "videos.upload_url",
        "parameters": [
            {
                "attribute": "id",
                "description": "Video ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.VideosUploadUrlIdParameter",
                "name": "id",
                "required": True,
                "type": "string",
            },
        ],
        "path": "/v1/videos/{id}:upload-url",
        "path_params": {"id": "550e8400-e29b-41d4-a716-446655440000"},
        "query": {},
        "response_model": "src.schemas.generated.uploads.SourceUpload",
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


# PATCH


@pytest.mark.api_case(
    _CASES["videos.update_video"],
)
@pytest.mark.usefixtures("arrange_videos_update_video")
async def test_update_video_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["videos.update_video"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_videos_update_video")
async def test_update_video_422_path_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


# POST


@pytest.mark.api_case(
    _CASES["videos.create_video"],
)
@pytest.mark.usefixtures("arrange_videos_create_video")
async def test_create_video_201(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["videos.upload_url"],
)
@pytest.mark.usefixtures("arrange_videos_upload_url")
async def test_upload_url_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["videos.upload_url"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_videos_upload_url")
async def test_upload_url_422_path_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()
