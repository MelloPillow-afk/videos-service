# Generated; do not edit.
# fmt: off
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field

from src.schemas.generated.schema_support import WireModel, validate_format

type JobStatus = Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"]

class Job(WireModel):
    model_config = ConfigDict(extra='allow')
    content_id: Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))] = Field(
        description="ID of the resource this job processes. Currently always a video ID.",
    )
    id: Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]
    message: str | None = Field(
        description="Readable explanation of a failed job; null otherwise.",
    )
    status: JobStatus = Field(
        description="Whether the job is queued, running, succeeded, or failed.",
    )
