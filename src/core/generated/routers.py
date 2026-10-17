# Generated; do not edit.
# fmt: off
from fastapi import FastAPI

from src.core.generated.authentication import require_authenticator
from src.handlers.generated.admin_jobs import router as _admin_jobs_router
from src.handlers.generated.admin_thumbnails import router as _admin_thumbnails_router
from src.handlers.generated.admin_videos import router as _admin_videos_router
from src.handlers.generated.health import router as _health_router
from src.handlers.generated.playback import router as _playback_router
from src.handlers.generated.videos import router as _videos_router


def register_routers(app: FastAPI) -> None:
    require_authenticator(app)
    app.include_router(_admin_jobs_router)
    app.include_router(_admin_thumbnails_router)
    app.include_router(_admin_videos_router)
    app.include_router(_health_router)
    app.include_router(_playback_router)
    app.include_router(_videos_router)
