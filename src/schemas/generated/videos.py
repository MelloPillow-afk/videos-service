# Generated; do not edit.
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field, model_validator

from src.schemas.generated.schema_support import (
    WireModel,
    omitted,
    require_properties,
    validate_format,
)

if TYPE_CHECKING:
    from src.schemas.generated import shared as _schema_shared
    from src.schemas.generated import thumbnails as _schema_thumbnails


type PublicationStatus = Literal["DRAFT", "PUBLISHED"]


class VideoDeletion(WireModel):
    model_config = ConfigDict(extra="allow")
    status: Literal["DELETING"]
    video_id: Annotated[str, AfterValidator(lambda value: validate_format(value, "uuid"))]


type VideoDescription = Annotated[str, Field(max_length=5000)] | None


class VideoRetry(WireModel):
    model_config = ConfigDict(extra="allow")
    attempt: Annotated[int, Field(ge=2)] = Field(description="Processing attempt number.")
    processing_job_id: Annotated[str, AfterValidator(lambda value: validate_format(value, "uuid"))]
    status: Literal["QUEUED"]
    video_id: Annotated[str, AfterValidator(lambda value: validate_format(value, "uuid"))]


type VideoStatus = Literal[
    "CREATED", "UPLOADING", "QUEUED", "PROCESSING", "READY", "FAILED", "DELETING"
]

type VideoTitle = Annotated[str, Field(min_length=1, max_length=200, pattern="\\S")]


class VideoProcessingError(WireModel):
    model_config = ConfigDict(extra="allow")
    code: str = Field(description="Code identifying the processing failure.")
    message: str = Field(description="Readable explanation of the processing failure.")


class Video(WireModel):
    model_config = ConfigDict(extra="allow")
    created_at: _schema_shared.Timestamp = Field(description="Date and time in UTC.")
    description: VideoDescription = Field(description="Optional video description.")
    duration_seconds: Annotated[float, Field(ge=0)] | None = Field(
        description="Video length in seconds."
    )
    id: Annotated[str, AfterValidator(lambda value: validate_format(value, "uuid"))]
    processing_error: VideoProcessingError = Field(
        default_factory=omitted, description="Processing failure details."
    )
    publication_status: PublicationStatus = Field(
        description="Whether the video is a draft or published."
    )
    published_at: (
        Annotated[str, AfterValidator(lambda value: validate_format(value, "date-time"))] | None
    ) = Field(description="When the video was published.")
    size_bytes: Annotated[int, Field(ge=1)] | None = Field(
        description="Uploaded file size in bytes."
    )
    status: VideoStatus = Field(description="Current video processing or deletion status.")
    thumbnail: _schema_thumbnails.ThumbnailImage = Field(description="The current thumbnail.")
    title: VideoTitle = Field(description="Video title.")
    updated_at: _schema_shared.Timestamp = Field(description="Date and time in UTC.")


class VideoCreate(WireModel):
    model_config = ConfigDict(extra="allow")
    description: VideoDescription = Field(
        default_factory=omitted, description="Optional video description."
    )
    title: VideoTitle = Field(description="Video title.")


class VideoUpdate(WireModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "anyOf": [
                {"required": ["title"]},
                {"required": ["description"]},
                {"required": ["publication_status"]},
            ]
        },
    )
    description: VideoDescription = Field(
        default_factory=omitted, description="Optional video description."
    )
    publication_status: PublicationStatus = Field(
        default_factory=omitted, description="Whether the video is a draft or published."
    )
    title: VideoTitle = Field(default_factory=omitted, description="Video title.")

    @model_validator(mode="before")
    @classmethod
    def _require_present(cls, value: object) -> object:
        return require_properties(value, [["title"], ["description"], ["publication_status"]])


class VideosPagination(WireModel):
    model_config = ConfigDict(extra="allow")
    has_more: bool = Field(description="Whether another page of results is available.")
    next_page_token: str | None = Field(description="Token for the next page.")


class Videos(WireModel):
    model_config = ConfigDict(extra="allow")
    data: list[Video]
    pagination: VideosPagination
