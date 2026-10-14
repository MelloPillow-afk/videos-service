# Generated; do not edit.
# fmt: off
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field

from src.schemas.generated.schema_support import WireModel, validate_format

if TYPE_CHECKING:
    from src.schemas.generated import shared as _schema_shared



class PlaybackPlayback(WireModel):
    model_config = ConfigDict(strict=True, extra='allow')
    type: Literal["hls"]
    url: _schema_shared.DeliveryUrl = Field(description="HTTPS link to the media.")

class Playback(WireModel):
    model_config = ConfigDict(strict=True, extra='allow')
    playback: PlaybackPlayback
    video_id: Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]
