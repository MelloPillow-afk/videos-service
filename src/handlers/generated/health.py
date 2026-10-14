# Generated; do not edit.
# fmt: off
import json

from src.core.generated.runtime import HandlerResponse, endpoint, model_adapter
from src.schemas.generated.health import Ping as _GetResourceResponse


@endpoint("health.get_resource")
async def get_resource() -> HandlerResponse[_GetResourceResponse]:
    return HandlerResponse(payload=model_adapter("src.schemas.generated.health.Ping").validate_json(json.dumps({"status": "ok"}), strict=True), headers={})
