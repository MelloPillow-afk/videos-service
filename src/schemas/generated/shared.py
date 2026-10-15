# Generated; do not edit.
# fmt: off
from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, Field

from src.schemas.generated.schema_support import validate_format

type DeliveryUrl = Annotated[str, Field(pattern="^https://"), AfterValidator(lambda value: validate_format(value, 'uri'))]

type Timestamp = Annotated[str, AfterValidator(lambda value: validate_format(value, 'date-time'))]
