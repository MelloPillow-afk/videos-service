# Generated; do not edit.
from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, Field

from src.schemas.generated.schema_support import validate_format

type VideosGetCollectionCursorParameter = str

type VideosGetCollectionLimitParameter = Annotated[int, Field(ge=1, le=100)]

type VideosGetCollectionSearchParameter = Annotated[str, Field(max_length=200)]

type VideosDeleteResourceIdParameter = Annotated[
    str, AfterValidator(lambda value: validate_format(value, "uuid"))
]

type VideosGetResourceIdParameter = Annotated[
    str, AfterValidator(lambda value: validate_format(value, "uuid"))
]

type VideosUpdateResourceIdParameter = Annotated[
    str, AfterValidator(lambda value: validate_format(value, "uuid"))
]

type SourceUploadsCompleteResourceIdParameter = Annotated[
    str, AfterValidator(lambda value: validate_format(value, "uuid"))
]

type PlaybackGetResourceIdParameter = Annotated[
    str, AfterValidator(lambda value: validate_format(value, "uuid"))
]

type VideosRetryProcessingIdParameter = Annotated[
    str, AfterValidator(lambda value: validate_format(value, "uuid"))
]

type ThumbnailsDeleteResourceIdParameter = Annotated[
    str, AfterValidator(lambda value: validate_format(value, "uuid"))
]

type ThumbnailUploadsCompleteResourceIdParameter = Annotated[
    str, AfterValidator(lambda value: validate_format(value, "uuid"))
]

type ThumbnailUploadsCreateResourceIdParameter = Annotated[
    str, AfterValidator(lambda value: validate_format(value, "uuid"))
]

type SourceUploadsCreateResourceIdParameter = Annotated[
    str, AfterValidator(lambda value: validate_format(value, "uuid"))
]
