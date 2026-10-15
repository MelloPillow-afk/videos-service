# Generated; do not edit.
# fmt: off
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field

from src.schemas.generated.schema_support import WireModel, validate_format

if TYPE_CHECKING:
    from src.schemas.generated import uploads as _schema_uploads


type ThumbnailSource = Literal["GENERATED", "CUSTOM", "NONE"]

type ThumbnailStatus = Literal["PENDING", "READY", "FAILED"]

class ThumbnailImage(WireModel):
    model_config = ConfigDict(extra='allow')
    source: ThumbnailSource = Field(description="Thumbnail source.")
    status: ThumbnailStatus = Field(description="Whether the thumbnail is pending, ready, or failed.")
    url: Annotated[str, Field(pattern="^https://"), AfterValidator(lambda value: validate_format(value, 'uri'))] | None = Field(description="Thumbnail image URL.")

class Thumbnail(WireModel):
    model_config = ConfigDict(extra='allow')
    thumbnail: ThumbnailImage = Field(description="The current thumbnail.")
    video_id: Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

class ThumbnailUploadCreate(WireModel):
    model_config = ConfigDict(extra='allow')
    content_type: Annotated[str, Field(min_length=1)] = Field(description="Image media type, such as image/jpeg.")
    file_name: Annotated[str, Field(min_length=1)] = Field(description="Name of the image file.")
    size_bytes: Annotated[int, Field(ge=1)] = Field(description="File size in bytes.")

class ThumbnailUpload(WireModel):
    model_config = ConfigDict(extra='allow')
    upload: _schema_uploads.Upload = Field(description="File upload URL and instructions.")
    video_id: Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]
