# Generated; do not edit.
# fmt: off
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field

from src.schemas.generated.schema_support import WireModel, validate_format

if TYPE_CHECKING:
    from src.schemas.generated import uploads as _schema_uploads



class ThumbnailSize(WireModel):
    model_config = ConfigDict(extra='allow')
    height: Annotated[int, Field(ge=1)] = Field(description="Height in pixels.")
    url: Annotated[
        str,
        Field(pattern="^https://"),
        AfterValidator(lambda value: validate_format(value, 'uri')),
    ] = Field(
        description="Image URL.",
    )
    width: Annotated[int, Field(ge=1)] = Field(description="Width in pixels.")

class ThumbnailSizesValue(WireModel):
    model_config = ConfigDict(extra='allow')
    lg: ThumbnailSize = Field(
        description="960 × 540, for featured content and large cards.",
    )
    md: ThumbnailSize = Field(description="640 × 360, for desktop cards and tablet grids.")
    sm: ThumbnailSize = Field(description="320 × 180, for mobile video cards.")
    xl: ThumbnailSize = Field(
        description="1280 × 720, for full-width banners and large displays.",
    )
    xs: ThumbnailSize = Field(description="160 × 90, for tiny previews and compact lists.")


type ThumbnailSizes = ThumbnailSizesValue | None

type ThumbnailSource = Literal["GENERATED", "CUSTOM", "NONE"]

type ThumbnailStatus = Literal["PENDING", "READY", "FAILED"]

class ThumbnailImage(WireModel):
    model_config = ConfigDict(extra='allow')
    sizes: ThumbnailSizes = Field(
        description="The thumbnail rendered at every 16:9 size, so clients pick one for their layout or build a srcset; null until the thumbnail is ready.",
    )
    source: ThumbnailSource = Field(description="Thumbnail source.")
    status: ThumbnailStatus = Field(
        description="Whether the thumbnail is pending, ready, or failed.",
    )
    url: Annotated[
        str,
        Field(pattern="^https://"),
        AfterValidator(lambda value: validate_format(value, 'uri')),
    ] | None = Field(
        description="The XL image URL, for clients that need only one size.",
    )

class Thumbnail(WireModel):
    model_config = ConfigDict(extra='allow')
    thumbnail: ThumbnailImage = Field(description="The current thumbnail.")
    video_id: Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

class ThumbnailUploadCreate(WireModel):
    model_config = ConfigDict(extra='allow')
    content_type: Literal["image/jpeg", "image/png", "image/webp"] = Field(
        description="Image media type.",
    )
    file_name: Annotated[str, Field(min_length=1)] = Field(
        description="Name of the image file.",
    )
    size_bytes: Annotated[int, Field(ge=1)] = Field(description="File size in bytes.")

class ThumbnailUpload(WireModel):
    model_config = ConfigDict(extra='allow')
    upload: _schema_uploads.Upload = Field(description="File upload URL and instructions.")
    video_id: Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]
