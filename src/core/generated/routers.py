# Generated; do not edit.
from fastapi import FastAPI

from src.handlers.generated.health import router as _health_router
from src.handlers.generated.playback import router as _playback_router
from src.handlers.generated.source_uploads import router as _source_uploads_router
from src.handlers.generated.thumbnail_uploads import router as _thumbnail_uploads_router
from src.handlers.generated.thumbnails import router as _thumbnails_router
from src.handlers.generated.videos import router as _videos_router


def register_routers(app: FastAPI) -> None:
    app.include_router(_health_router)
    app.include_router(_playback_router)
    app.include_router(_source_uploads_router)
    app.include_router(_thumbnail_uploads_router)
    app.include_router(_thumbnails_router)
    app.include_router(_videos_router)
