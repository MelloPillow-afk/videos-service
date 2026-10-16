# Generated; do not edit.
# fmt: off
from typing import Any

import pytest
from httpx import AsyncClient

from ._support import APICase

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_CASES: dict[str, dict[str, Any]] = {
    "thumbnails.complete_upload": {
        "body": {"upload_id": "04d1790f-f941-4ba6-8d97-0e6830ca4394"},
        "body_model": {
            "attribute": "body",
            "model": "src.schemas.generated.uploads.UploadComplete",
            "required": True,
            "source": "/private/tmp/videos-showcase-mel12/api-specs/schemas/uploads/upload_complete.yaml#",
        },
        "expected_body": {
            "thumbnail": {
                "source": "CUSTOM",
                "status": "READY",
                "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        "expected_status": 200,
        "method": "POST",
        "operation_id": "thumbnails.complete_upload",
        "parameters": [
            {
                "attribute": "id",
                "description": "Video ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.ThumbnailsCompleteUploadIdParameter",
                "name": "id",
                "required": True,
                "type": "string",
            },
        ],
        "path": "/v1/videos/{id}/thumbnails:complete-upload",
        "path_params": {"id": "550e8400-e29b-41d4-a716-446655440000"},
        "query": {},
        "response_model": "src.schemas.generated.thumbnails.Thumbnail",
    },
    "thumbnails.delete_thumbnail": {
        "body": None,
        "body_model": None,
        "expected_body": {
            "thumbnail": {
                "source": "CUSTOM",
                "status": "READY",
                "url": "https://media.example.com/videos/550e8400-e29b-41d4-a716-446655440000/thumbnails/custom-v2.jpg",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        "expected_status": 200,
        "method": "DELETE",
        "operation_id": "thumbnails.delete_thumbnail",
        "parameters": [
            {
                "attribute": "id",
                "description": "Video ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.ThumbnailsDeleteThumbnailIdParameter",
                "name": "id",
                "required": True,
                "type": "string",
            },
        ],
        "path": "/v1/videos/{id}/thumbnails",
        "path_params": {"id": "550e8400-e29b-41d4-a716-446655440000"},
        "query": {},
        "response_model": "src.schemas.generated.thumbnails.Thumbnail",
    },
    "thumbnails.upload_url": {
        "body": {"content_type": "image/jpeg", "file_name": "faith-cover.jpg", "size_bytes": 183420},
        "body_model": {
            "attribute": "body",
            "model": "src.schemas.generated.thumbnails.ThumbnailUploadCreate",
            "required": True,
            "source": "/private/tmp/videos-showcase-mel12/api-specs/schemas/thumbnails/thumbnail_upload_create.yaml#",
        },
        "expected_body": {
            "upload": {
                "expires_at": "2026-10-13T14:15:00Z",
                "headers": {"Content-Type": "image/jpeg"},
                "method": "PUT",
                "upload_id": "50fd0382-794f-4c9b-9a12-60e92a89e008",
                "url": "https://uploads.example.com/thumbnail.jpg?signature=example",
            },
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        "expected_status": 200,
        "method": "POST",
        "operation_id": "thumbnails.upload_url",
        "parameters": [
            {
                "attribute": "id",
                "description": "Video ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.ThumbnailsUploadUrlIdParameter",
                "name": "id",
                "required": True,
                "type": "string",
            },
        ],
        "path": "/v1/videos/{id}/thumbnails:upload-url",
        "path_params": {"id": "550e8400-e29b-41d4-a716-446655440000"},
        "query": {},
        "response_model": "src.schemas.generated.thumbnails.ThumbnailUpload",
    },
}


# DELETE


@pytest.mark.api_case(
    _CASES["thumbnails.delete_thumbnail"],
)
@pytest.mark.usefixtures("arrange_thumbnails_delete_thumbnail")
async def test_delete_thumbnail_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["thumbnails.delete_thumbnail"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_thumbnails_delete_thumbnail")
async def test_delete_thumbnail_422_path_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


# POST


@pytest.mark.api_case(
    _CASES["thumbnails.complete_upload"],
)
@pytest.mark.usefixtures("arrange_thumbnails_complete_upload")
async def test_complete_upload_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["thumbnails.complete_upload"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_thumbnails_complete_upload")
async def test_complete_upload_422_path_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["thumbnails.upload_url"],
)
@pytest.mark.usefixtures("arrange_thumbnails_upload_url")
async def test_upload_url_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["thumbnails.upload_url"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_thumbnails_upload_url")
async def test_upload_url_422_path_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()
