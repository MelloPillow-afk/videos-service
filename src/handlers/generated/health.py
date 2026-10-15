# Generated; do not edit.
# fmt: off
from fastapi import APIRouter as _generator_APIRouter
from pydantic import TypeAdapter as _generator_TypeAdapter

from src.core.generated.overrides import select_endpoint as _generator_select_endpoint
from src.schemas.generated.health import Ping as _PingResponse

router = _generator_APIRouter(prefix="")


@router.get(
    "/ping",
    response_model=_PingResponse,
    status_code=200,
    response_model_exclude_unset=True,
)
@_generator_select_endpoint("health.ping")
async def ping() -> _PingResponse:
    return _generator_TypeAdapter(_PingResponse).validate_python({"status": "ok"})
