# Generated; do not edit.
# fmt: off
from typing import Any

import pytest
from httpx import AsyncClient

from ._support import APICase

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_CASES: dict[str, dict[str, Any]] = {
    "jobs.get_job": {
        "authentication": None,
        "body": None,
        "body_model": None,
        "expected_body": {
            "id": "e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0",
            "message": None,
            "status": "QUEUED",
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
        "expected_status": 200,
        "method": "GET",
        "operation_id": "jobs.get_job",
        "parameters": [
            {
                "attribute": "job_id",
                "description": "Job ID.",
                "in": "path",
                "model": "src.schemas.generated.operations.JobsGetJobJobIdParameter",
                "name": "job_id",
                "required": True,
                "type": "string",
            },
        ],
        "path": "/v1/jobs/{job_id}",
        "path_params": {"job_id": "e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0"},
        "query": {},
        "response_model": "src.schemas.generated.jobs.Job",
    },
}


# GET


@pytest.mark.api_case(
    _CASES["jobs.get_job"],
)
@pytest.mark.usefixtures("arrange_jobs_get_job")
async def test_get_job_200(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()


@pytest.mark.api_case(
    _CASES["jobs.get_job"], mutation={
        "error_types": ["value_error"],
        "in": "path",
        "name": "job_id",
        "value": "not a valid value",
    },
)
@pytest.mark.usefixtures("arrange_jobs_get_job")
async def test_get_job_422_path_job_id_invalid_format(api_case: APICase, api_client: AsyncClient) -> None:
    # Arrange
    request = api_case.prepare_request()

    # Act
    api_case.response = await api_client.request(**request)

    # Assert
    api_case.assert_response()
