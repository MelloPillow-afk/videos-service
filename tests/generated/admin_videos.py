# Generated; do not edit.
# fmt: off
from typing import Any

import pytest
from httpx import AsyncClient

from ._support import APICase

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_CASES: dict[str, dict[str, Any]] = {
    "admin_videos.create_video": {
        "authentication": "required",
        "body": {"description": "An introductory lesson", "title": "Introduction to Faith"},
        "body_model": {
            "attribute": "body",
            "model": "src.schemas.generated.videos.VideoCreate",
            "required": True,
            "source": "/Users/richardhuynh/Dev/personal/projects/pilgrims/videos-service/api-specs/schemas/videos/video_create.yaml#",
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
            "thumbnail": {"source": "NONE", "status": "PENDING", "url": None},
            "title": "Introduction to Faith",
            "updated_at": "2026-10-13T14:00:00Z",
        },
        "expected_status": 201,
        "method": "POST",
        "operation_id": "admin_videos.create_video",
        "parameters": [],
        "path": "/v1/admin/videos",
        "path_params": {},
        "query": {},
        "response_model": "src.schemas.generated.videos.Video",
    },
    "admin_videos.delete_video": {
        "authentication": "required",
        "body": None,
        "body_model": None,
        "expected_body": None,
        "expected_status": 204,
        "method": "DELETE",
        "operation_id": "admin_videos.delete_video",
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
    "admin_videos.get_video": {
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
            "thumbnail": {"source": "NONE", "status": "PENDING", "url": None},
            "title": "Introduction to Faith",
            "updated_at": "2026-10-13T14:00:00Z",
        },
        "expected_status": 200,
        "method": "GET",
        "operation_id": "admin_videos.get_video",
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
        "response_model": "src.schemas.generated.videos.Video",
    },
    "admin_videos.update_video": {
        "authentication": "required",
        "body": {
            "description": "An introductory lesson",
            "publication_status": "DRAFT",
            "title": "Introduction to Faith",
        },
        "body_model": {
            "attribute": "body",
            "model": "src.schemas.generated.videos.VideoUpdate",
            "required": True,
            "source": "/Users/richardhuynh/Dev/personal/projects/pilgrims/videos-service/api-specs/schemas/videos/video_update.yaml#",
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
            "thumbnail": {"source": "NONE", "status": "PENDING", "url": None},
            "title": "Introduction to Faith",
            "updated_at": "2026-10-13T14:00:00Z",
        },
        "expected_status": 200,
        "method": "PATCH",
        "operation_id": "admin_videos.update_video",
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
        "response_model": "src.schemas.generated.videos.Video",
    },
    "admin_videos.upload_url": {
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
        "operation_id": "admin_videos.upload_url",
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
    _CASES["admin_videos.delete_video"],
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
    _CASES["admin_videos.delete_video"], unauthenticated=True,
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
    _CASES["admin_videos.delete_video"], mutation={
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
    _CASES["admin_videos.get_video"],
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
    _CASES["admin_videos.get_video"], unauthenticated=True,
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
    _CASES["admin_videos.get_video"], mutation={
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


# PATCH


@pytest.mark.api_case(
    _CASES["admin_videos.update_video"],
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
    _CASES["admin_videos.update_video"], unauthenticated=True,
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
    _CASES["admin_videos.update_video"], mutation={
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
    _CASES["admin_videos.create_video"],
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
    _CASES["admin_videos.create_video"], unauthenticated=True,
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
    _CASES["admin_videos.upload_url"],
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
    _CASES["admin_videos.upload_url"], unauthenticated=True,
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
    _CASES["admin_videos.upload_url"], mutation={
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
