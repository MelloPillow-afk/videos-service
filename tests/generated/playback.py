# Generated; do not edit.
# fmt: off
from typing import Any

import pytest
from httpx import AsyncClient

from ._support import APICase

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_CASES: dict[str, dict[str, Any]] = {
    "playback.get_playback": {
        "authentication": "optional",
        "body": None,
        "body_model": None,
        "expected_body": {
            "playback": {"type": "hls", "url": "https://media.example.com/videos/intro/hls/master.m3u8"},
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        "expected_status": 200,
        "method": "GET",
        "operation_id": "playback.get_playback",
        "parameters": [
            {
                "attribute": "id",
                "description": "Video ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.PlaybackGetPlaybackIdParameter",
                "name": "id",
                "required": True,
                "type": "string",
            },
        ],
        "path": "/v1/videos/{id}/playback",
        "path_params": {"id": "550e8400-e29b-41d4-a716-446655440000"},
        "query": {},
        "response_model": "src.schemas.generated.playback.Playback",
    },
}


# GET


@pytest.mark.api_case(
    _CASES["playback.get_playback"],
)
@pytest.mark.usefixtures("arrange_playback_get_playback")
async def test_get_playback_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["playback.get_playback"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_playback_get_playback")
async def test_get_playback_422_path_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()
