# Generated; do not edit.
# fmt: off
import json as _generator_json

from src.core.generated.runtime import HandlerResponse as _generator_HandlerResponse
from src.core.generated.runtime import endpoint as _generator_endpoint
from src.core.generated.runtime import model_adapter as _generator_model_adapter
from src.schemas.generated.health import Ping as _GetResourceResponse


@_generator_endpoint("health.get_resource")
async def get_resource() -> _generator_HandlerResponse[_GetResourceResponse]:
    return _generator_HandlerResponse(payload=_generator_model_adapter("src.schemas.generated.health.Ping").validate_json(_generator_json.dumps({"status": "ok"}), strict=True), headers={})
