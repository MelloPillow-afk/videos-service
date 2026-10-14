# Generated; do not edit.
# fmt: off
from __future__ import annotations

from pydantic import ConfigDict, Field

from src.schemas.generated.schema_support import WireModel


class ErrorError(WireModel):
    model_config = ConfigDict(strict=True, extra='allow')
    code: str = Field(description="Code identifying the error.")
    message: str = Field(description="Readable explanation of the error.")

class Error(WireModel):
    model_config = ConfigDict(strict=True, extra='allow')
    error: ErrorError
