"""Wire projections shared by handwritten video and thumbnail handlers."""

from urllib.parse import quote

from src.domain.videos import VideoRecord
from src.schemas.generated.videos import Video


def delivery_url(origin: str, key: str) -> str:
    return origin.rstrip("/") + "/" + quote(key.lstrip("/"), safe="/")


def video_response(video: VideoRecord, cdn_origin: str = "https://media.example.com") -> Video:
    key = video.custom_thumbnail_key
    source = "CUSTOM"
    if key is None and video.generated_thumbnail_status == "READY":
        key = video.generated_thumbnail_key
        source = "GENERATED"
    thumbnail = {
        "status": "READY"
        if key
        else ("FAILED" if video.generated_thumbnail_status == "FAILED" else "PENDING"),
        "source": source if key else "NONE",
        "url": delivery_url(cdn_origin, key) if key else None,
    }
    error: dict[str, object] = {}
    if video.processing_error_code and video.processing_error_message:
        error["processing_error"] = {
            "code": video.processing_error_code,
            "message": video.processing_error_message,
        }
    return Video.model_validate(
        {
            "id": str(video.id),
            "title": video.title,
            "description": video.description,
            "status": video.status,
            "publication_status": video.publication_status,
            "size_bytes": video.size_bytes,
            "duration_seconds": video.duration_seconds,
            "thumbnail": thumbnail,
            "published_at": video.published_at.isoformat().replace("+00:00", "Z")
            if video.published_at
            else None,
            "created_at": video.created_at.isoformat().replace("+00:00", "Z"),
            "updated_at": video.updated_at.isoformat().replace("+00:00", "Z"),
            **error,
        }
    )
