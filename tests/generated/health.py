# Generated; do not edit.
# fmt: off
from typing import Any

import pytest
from httpx import AsyncClient

from ._support import APICase

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_CASES: dict[str, dict[str, Any]] = {
    "health.ping": {
        "authentication": None,
        "body": None,
        "body_model": None,
        "expected_body": {"status": "ok"},
        "expected_status": 200,
        "method": "GET",
        "operation_id": "health.ping",
        "parameters": [],
        "path": "/ping",
        "path_params": {},
        "query": {},
        "response_model": "src.schemas.generated.health.Ping",
    },
}


# GET


@pytest.mark.api_case(
    _CASES["health.ping"],
)
@pytest.mark.usefixtures("arrange_health_ping")
async def test_ping_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()
