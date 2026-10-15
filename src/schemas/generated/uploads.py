# Generated; do not edit.
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field

from src.schemas.generated.schema_support import WireModel, validate_format

if TYPE_CHECKING:
    from src.schemas.generated import shared as _schema_shared
    from src.schemas.generated import thumbnails as _schema_thumbnails
    from src.schemas.generated import videos as _schema_videos


class SourceUploadCreate(WireModel):
    model_config = ConfigDict(extra="allow")
    content_type: Literal["video/mp4"] = Field(description="Video media type.")
    file_name: Annotated[str, Field(min_length=1)] = Field(description="Name of the video file.")
    size_bytes: Annotated[int, Field(ge=1)] = Field(description="File size in bytes.")


class UploadHeaders(WireModel):
    model_config = ConfigDict(extra="allow")
    Content_Type: str = Field(alias="Content-Type")
    __pydantic_extra__: dict[str, str] = Field(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]


class Upload(WireModel):
    model_config = ConfigDict(extra="allow")
    expires_at: _schema_shared.Timestamp = Field(description="Date and time in UTC.")
    headers: UploadHeaders = Field(description="Headers to include with the upload.")
    method: Literal["PUT"]
    upload_id: Annotated[str, AfterValidator(lambda value: validate_format(value, "uuid"))]
    url: Annotated[
        str, Field(pattern="^https://"), AfterValidator(lambda value: validate_format(value, "uri"))
    ] = Field(description="URL to use for uploading the file.")


class SourceUpload(WireModel):
    model_config = ConfigDict(extra="allow")
    status: Literal["UPLOADING"]
    upload: Upload = Field(description="File upload URL and instructions.")
    video_id: Annotated[str, AfterValidator(lambda value: validate_format(value, "uuid"))]


class UploadComplete(WireModel):
    model_config = ConfigDict(extra="allow")
    upload_id: Annotated[str, AfterValidator(lambda value: validate_format(value, "uuid"))] = Field(
        description="Upload ID returned with the upload URL."
    )


class SourceUploadProcessing(WireModel):
    model_config = ConfigDict(extra="allow")
    processing_job_id: Annotated[
        str, AfterValidator(lambda value: validate_format(value, "uuid"))
    ] = Field(description="Processing job ID.")
    status: _schema_videos.VideoStatus = Field(description="Current video status.")
    thumbnail_status: _schema_thumbnails.ThumbnailStatus = Field(description="Thumbnail status.")
    video_id: Annotated[str, AfterValidator(lambda value: validate_format(value, "uuid"))]
