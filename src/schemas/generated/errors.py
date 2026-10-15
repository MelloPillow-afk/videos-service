# Generated; do not edit.
from __future__ import annotations

from pydantic import ConfigDict, Field

from src.schemas.generated.schema_support import WireModel


class Error(WireModel):
    model_config = ConfigDict(extra="allow")
    detail: str = Field(description="Readable explanation of the error.")
