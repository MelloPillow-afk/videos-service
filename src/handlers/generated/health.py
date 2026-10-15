# Generated; do not edit.
# fmt: off
from fastapi import APIRouter as _generator_APIRouter
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.health import Ping as _GetResourceResponse

router = _generator_APIRouter(prefix="")


@router.get("/ping", response_model=_GetResourceResponse, status_code=200, response_model_exclude_unset=True, operation_id="health.get_resource", tags=["Health"], summary="Get Health", description="Check API reachability. Does not check the database.", responses={"200": {"content": {"application/json": {}}, "description": "The API is responding."}, "500": {"content": {"text/plain": {"schema": {"examples": ["Internal Server Error"], "type": "string"}}}, "description": "An unexpected server failure. Production responses do not include exception details."}}, openapi_extra={"security": []})
@_generator_select_endpoint("health.get_resource")
async def get_resource() -> _GetResourceResponse:
    return _generator_TypeAdapter(_GetResourceResponse).validate_python({"status": "ok"})
