# Generated; do not edit.
from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict

from src.schemas.generated.schema_support import WireModel


class Ping(WireModel):
    model_config = ConfigDict(extra="allow")
    status: Literal["ok"]
