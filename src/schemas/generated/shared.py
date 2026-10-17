# Generated; do not edit.
# fmt: off
from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, ConfigDict, Field

from src.schemas.generated.schema_support import WireModel, validate_format

type DeliveryUrl = Annotated[
    str,
    Field(pattern="^https://"),
    AfterValidator(lambda value: validate_format(value, 'uri')),
]

class Pagination(WireModel):
    model_config = ConfigDict(extra='allow')
    has_more: bool = Field(description="Whether another page of results is available.")
    next_page_token: str | None = Field(
        description="Token for the next page, or null on the last page.",
    )

type Timestamp = Annotated[str, AfterValidator(lambda value: validate_format(value, 'date-time'))]
