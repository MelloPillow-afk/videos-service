# Generated; do not edit.
# fmt: off
from typing import Annotated as _generator_Annotated

from fastapi import APIRouter as _generator_APIRouter
from fastapi import Depends as _generator_Depends
from fastapi import Path as _generator_Path
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.authentication import (
    require_authentication as _generator_require_authentication,
)
from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.jobs import Job as _GetJobResponse
from src.schemas.generated.operations import (
    AdminJobsGetJobJobIdParameter as _GetJobJobIdParameter,
)

router = _generator_APIRouter(prefix="/v1/admin/jobs")


@router.get(
    "/{job_id}",
    response_model=_GetJobResponse,
    status_code=200,
    response_model_exclude_unset=True,
    dependencies=[_generator_Depends(_generator_require_authentication)],
)
@_generator_select_endpoint("admin_jobs.get_job")
async def get_job(
    *,
    job_id: _generator_Annotated[
        _GetJobJobIdParameter,
        _generator_Path(alias="job_id", description="Job ID."),
    ],
) -> _GetJobResponse:
    return _generator_TypeAdapter(_GetJobResponse).validate_python(
        {
            "id": "e9f1c6d0-4e8b-4a23-a52a-21a3d51127d0",
            "message": None,
            "status": "QUEUED",
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
        },
    )
