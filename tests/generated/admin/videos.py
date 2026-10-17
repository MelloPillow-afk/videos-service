# Generated; do not edit.
# fmt: off
from typing import Any

import pytest
from httpx import AsyncClient

from .._support import APICase

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_CASES: dict[str, dict[str, Any]] = {
    "admin.videos.create_video": {
        "authentication": "required",
        "body": {"description": "An introductory lesson", "title": "Introduction to Faith"},
        "body_model": {
            "attribute": "body",
            "model": "src.schemas.generated.videos.AdminVideoCreate",
            "required": True,
            "source": "/Users/richardhuynh/Dev/personal/projects/pilgrims/videos-service/api-specs/schemas/videos/admin_video_create.yaml#",
        },
        "expected_body": {
            "created_at": "2026-10-13T14:00:00Z",
            "description": "An introductory lesson",
            "duration_seconds": None,
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "latest_job_id": None,
            "publication_status": "DRAFT",
            "published_at": None,
            "size_bytes": None,
            "status": "CREATED",
            "thumbnail": {"sizes": None, "source": "NONE", "status": "PENDING", "url": None},
            "title": "Introduction to Faith",
            "updated_at": "2026-10-13T14:00:00Z",
        },
        "expected_status": 201,
        "method": "POST",
        "operation_id": "admin.videos.create_video",
        "parameters": [],
        "path": "/v1/admin/videos",
        "path_params": {},
        "query": {},
        "response_model": "src.schemas.generated.videos.AdminVideo",
    },
    "admin.videos.delete_video": {
        "authentication": "required",
        "body": None,
        "body_model": None,
        "expected_body": None,
        "expected_status": 204,
        "method": "DELETE",
        "operation_id": "admin.videos.delete_video",
        "parameters": [
            {
                "attribute": "id",
                "description": "Video ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.AdminVideosDeleteVideoIdParameter",
                "name": "id",
                "required": True,
                "type": "string",
            },
        ],
        "path": "/v1/admin/videos/{id}",
        "path_params": {"id": "550e8400-e29b-41d4-a716-446655440000"},
        "query": {},
        "response_model": None,
    },
    "admin.videos.get_video": {
        "authentication": "required",
        "body": None,
        "body_model": None,
        "expected_body": {
            "created_at": "2026-10-13T14:00:00Z",
            "description": "An introductory lesson",
            "duration_seconds": None,
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "latest_job_id": None,
            "publication_status": "DRAFT",
            "published_at": None,
            "size_bytes": None,
            "status": "CREATED",
            "thumbnail": {"sizes": None, "source": "NONE", "status": "PENDING", "url": None},
            "title": "Introduction to Faith",
            "updated_at": "2026-10-13T14:00:00Z",
        },
        "expected_status": 200,
        "method": "GET",
        "operation_id": "admin.videos.get_video",
        "parameters": [
            {
                "attribute": "id",
                "description": "Video ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.AdminVideosGetVideoIdParameter",
                "name": "id",
                "required": True,
                "type": "string",
            },
        ],
        "path": "/v1/admin/videos/{id}",
        "path_params": {"id": "550e8400-e29b-41d4-a716-446655440000"},
        "query": {},
        "response_model": "src.schemas.generated.videos.AdminVideo",
    },
    "admin.videos.list_videos": {
        "authentication": "required",
        "body": None,
        "body_model": None,
        "expected_body": {
            "data": [
                {
                    "created_at": "2026-10-13T14:00:00Z",
                    "description": "An introductory lesson",
                    "duration_seconds": None,
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "latest_job_id": None,
                    "publication_status": "DRAFT",
                    "published_at": None,
                    "size_bytes": None,
                    "status": "CREATED",
                    "thumbnail": {"sizes": None, "source": "NONE", "status": "PENDING", "url": None},
                    "title": "Introduction to Faith",
                    "updated_at": "2026-10-13T14:00:00Z",
                },
            ],
            "pagination": {"has_more": False, "next_page_token": None},
        },
        "expected_status": 200,
        "method": "GET",
        "operation_id": "admin.videos.list_videos",
        "parameters": [
            {
                "attribute": "limit",
                "default": 20,
                "description": "Maximum number of videos to return.",
                "in": "query",
                "model": "src.schemas.generated.operations.AdminVideosListVideosLimitParameter",
                "name": "limit",
                "required": False,
                "type": "integer",
            },
            {
                "attribute": "page_token",
                "description": "The next_page_token from the previous page.",
                "in": "query",
                "model": "src.schemas.generated.operations.AdminVideosListVideosPageTokenParameter",
                "name": "page_token",
                "required": False,
                "type": "string",
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
        ],
        "path": "/v1/admin/videos",
        "path_params": {},
        "query": {
            "limit": 20,
            "page_token": "eyJ0IjoiMjAyNi0xMC0xNFQwOTowMDowMC4wMDAwMDArMDA6MDAiLCJpZCI6IjNmMmI4YzFlLTdkNGEtNGU2Yi05YzBmLTVhMWQyZTNiNGM1ZCJ9",
            "publication_status": "DRAFT",
        },
        "response_model": "src.schemas.generated.videos.AdminVideos",
    },
    "admin.videos.update_video": {
        "authentication": "required",
        "body": {
            "description": "An introductory lesson",
            "publication_status": "DRAFT",
            "title": "Introduction to Faith",
        },
        "body_model": {
            "attribute": "body",
            "model": "src.schemas.generated.videos.AdminVideoUpdate",
            "required": True,
            "source": "/Users/richardhuynh/Dev/personal/projects/pilgrims/videos-service/api-specs/schemas/videos/admin_video_update.yaml#",
        },
        "expected_body": {
            "created_at": "2026-10-13T14:00:00Z",
            "description": "An introductory lesson",
            "duration_seconds": None,
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "latest_job_id": None,
            "publication_status": "DRAFT",
            "published_at": None,
            "size_bytes": None,
            "status": "CREATED",
            "thumbnail": {"sizes": None, "source": "NONE", "status": "PENDING", "url": None},
            "title": "Introduction to Faith",
            "updated_at": "2026-10-13T14:00:00Z",
        },
        "expected_status": 200,
        "method": "PATCH",
        "operation_id": "admin.videos.update_video",
        "parameters": [
            {
                "attribute": "id",
                "description": "Video ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.AdminVideosUpdateVideoIdParameter",
                "name": "id",
                "required": True,
                "type": "string",
            },
        ],
        "path": "/v1/admin/videos/{id}",
        "path_params": {"id": "550e8400-e29b-41d4-a716-446655440000"},
        "query": {},
        "response_model": "src.schemas.generated.videos.AdminVideo",
    },
    "admin.videos.upload_url": {
        "authentication": "required",
        "body": {"content_type": "video/mp4", "file_name": "introduction.mp4", "size_bytes": 524288000},
        "body_model": {
            "attribute": "body",
            "model": "src.schemas.generated.uploads.SourceUploadCreate",
            "required": True,
            "source": "/Users/richardhuynh/Dev/personal/projects/pilgrims/videos-service/api-specs/schemas/uploads/source_upload_create.yaml#",
        },
        "expected_body": {
            "status": "UPLOADING",
            "upload": {
                "expires_at": "2026-10-13T14:15:00Z",
                "headers": {"Content-Type": "video/mp4"},
                "method": "PUT",
                "upload_id": "04d1790f-f941-4ba6-8d97-0e6830ca4394",
                "url": "https://uploads.example.com/source.mp4?signature=example",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        "expected_status": 200,
        "method": "POST",
        "operation_id": "admin.videos.upload_url",
        "parameters": [
            {
                "attribute": "id",
                "description": "Video ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.AdminVideosUploadUrlIdParameter",
                "name": "id",
                "required": True,
                "type": "string",
            },
        ],
        "path": "/v1/admin/videos/{id}:upload-url",
        "path_params": {"id": "550e8400-e29b-41d4-a716-446655440000"},
        "query": {},
        "response_model": "src.schemas.generated.uploads.SourceUpload",
    },
}


# DELETE


@pytest.mark.api_case(
    _CASES["admin.videos.delete_video"],
)
@pytest.mark.usefixtures("arrange_admin_videos_delete_video")
async def test_delete_video_204(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.delete_video"], unauthenticated=True,
)
@pytest.mark.usefixtures("arrange_admin_videos_delete_video")
async def test_delete_video_401_missing_token(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.delete_video"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_admin_videos_delete_video")
async def test_delete_video_422_path_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


# GET


@pytest.mark.api_case(
    _CASES["admin.videos.get_video"],
)
@pytest.mark.usefixtures("arrange_admin_videos_get_video")
async def test_get_video_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.get_video"], unauthenticated=True,
)
@pytest.mark.usefixtures("arrange_admin_videos_get_video")
async def test_get_video_401_missing_token(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.get_video"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_admin_videos_get_video")
async def test_get_video_422_path_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.list_videos"],
)
@pytest.mark.usefixtures("arrange_admin_videos_list_videos")
async def test_list_videos_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.list_videos"], unauthenticated=True,
)
@pytest.mark.usefixtures("arrange_admin_videos_list_videos")
async def test_list_videos_401_missing_token(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.list_videos"], mutation={
        "error_types": ["less_than_equal", "greater_than_equal"],
        "in": "query",
        "name": "limit",
        "value": 101,
    },
)
@pytest.mark.usefixtures("arrange_admin_videos_list_videos")
async def test_list_videos_422_query_limit_above_maximum(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.list_videos"], mutation={
        "error_types": ["greater_than_equal", "less_than_equal"],
        "in": "query",
        "name": "limit",
        "value": 0,
    },
)
@pytest.mark.usefixtures("arrange_admin_videos_list_videos")
async def test_list_videos_422_query_limit_below_minimum(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.list_videos"], mutation={
        "error_types": ["int_parsing", "greater_than_equal", "less_than_equal"],
        "in": "query",
        "name": "limit",
        "value": "not-an-integer",
    },
)
@pytest.mark.usefixtures("arrange_admin_videos_list_videos")
async def test_list_videos_422_query_limit_invalid_type(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.list_videos"], mutation={
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
@pytest.mark.usefixtures("arrange_admin_videos_list_videos")
async def test_list_videos_422_query_publication_status_outside_allowed_values(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


# PATCH


@pytest.mark.api_case(
    _CASES["admin.videos.update_video"],
)
@pytest.mark.usefixtures("arrange_admin_videos_update_video")
async def test_update_video_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.update_video"], unauthenticated=True,
)
@pytest.mark.usefixtures("arrange_admin_videos_update_video")
async def test_update_video_401_missing_token(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.update_video"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_admin_videos_update_video")
async def test_update_video_422_path_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


# POST


@pytest.mark.api_case(
    _CASES["admin.videos.create_video"],
)
@pytest.mark.usefixtures("arrange_admin_videos_create_video")
async def test_create_video_201(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.create_video"], unauthenticated=True,
)
@pytest.mark.usefixtures("arrange_admin_videos_create_video")
async def test_create_video_401_missing_token(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.upload_url"],
)
@pytest.mark.usefixtures("arrange_admin_videos_upload_url")
async def test_upload_url_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.upload_url"], unauthenticated=True,
)
@pytest.mark.usefixtures("arrange_admin_videos_upload_url")
async def test_upload_url_401_missing_token(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["admin.videos.upload_url"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_admin_videos_upload_url")
async def test_upload_url_422_path_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()
