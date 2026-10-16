"""Shared transport mapping for source and custom-image admission failures."""

from fastapi import HTTPException

from src.domain.uploads import UploadRejected


def upload_rejection(error: UploadRejected) -> HTTPException:
    return HTTPException(
        {"missing": 404, "too_large": 413, "invalid": 400}[error.reason], error.message
    )
