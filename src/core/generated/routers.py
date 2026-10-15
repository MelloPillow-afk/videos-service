# Generated; do not edit.
# fmt: off
from fastapi import FastAPI

from src.handlers.generated.health import router as _health_router
from src.handlers.generated.playback import router as _playback_router
from src.handlers.generated.thumbnails import router as _thumbnails_router
from src.handlers.generated.videos import router as _videos_router


def register_routers(app: FastAPI) -> None:
    app.include_router(_health_router)
    app.include_router(_playback_router)
    app.include_router(_thumbnails_router)
    app.include_router(_videos_router)
