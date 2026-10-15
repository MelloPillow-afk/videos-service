# Generated; do not edit.
# fmt: off
from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, Field

from src.schemas.generated.schema_support import validate_format

type VideosListVideosCursorParameter = str

type VideosListVideosLimitParameter = Annotated[int, Field(ge=1, le=100)]

type VideosListVideosSearchParameter = Annotated[str, Field(max_length=200)]

type VideosDeleteVideoIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type VideosGetVideoIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type VideosUpdateVideoIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type PlaybackGetPlaybackIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type ThumbnailsDeleteThumbnailIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type ThumbnailsCompleteUploadIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type ThumbnailsUploadUrlIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type VideosCompleteUploadIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type VideosRetryProcessingIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]

type VideosUploadUrlIdParameter = Annotated[str, AfterValidator(lambda value: validate_format(value, 'uuid'))]
