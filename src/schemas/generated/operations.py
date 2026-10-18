# Generated; do not edit.
# fmt: off
from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, ConfigDict, Field

from src.schemas.generated.schema_support import WireModel, validate_format

type AdminVideosListVideosLimitParameter = Annotated[int, Field(ge=1, le=100)]

type AdminVideosListVideosPageTokenParameter = str

type AdminVideosDeleteVideoIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

class AdminVideosDeleteVideoResponse(WireModel):
    model_config = ConfigDict(extra='allow')
    pass

type AdminVideosGetVideoIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type AdminVideosUpdateVideoIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type AdminVideosGetPlaybackIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type AdminThumbnailsDeleteThumbnailIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type AdminThumbnailsCompleteUploadIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type AdminThumbnailsUploadUrlIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type AdminVideosCompleteUploadIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type AdminVideosUploadUrlIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type JobsGetJobJobIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type VideosListVideosLimitParameter = Annotated[int, Field(ge=1, le=100)]

type VideosListVideosPageTokenParameter = str

type VideosGetVideoIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type PlaybackGetPlaybackIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]
