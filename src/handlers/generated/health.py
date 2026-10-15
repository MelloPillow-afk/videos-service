# Generated; do not edit.
from fastapi import APIRouter as _generator_APIRouter
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.health import Ping as _GetResourceResponse

router = _generator_APIRouter(prefix="")


@router.get(
    "/ping",
    response_model=_GetResourceResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("health.get_resource")
async def get_resource() -> _GetResourceResponse:
    return _generator_TypeAdapter(_GetResourceResponse).validate_python({"status": "ok"})
