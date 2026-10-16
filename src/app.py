"""ASGI application factory and shared-resource lifecycle."""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import FastAPI

from src.config import Settings
from src.core.generated.routers import register_routers
from src.providers.cloud_run import CloudRunJobLauncher
from src.providers.identity import NeonIdentity, SigningKeys
from src.providers.jobs import JobLauncher
from src.providers.r2 import R2Storage
from src.providers.storage import Storage
from src.repositories import Database
from src.repositories.identity import NeonRoles
from src.services.authorization import Authorization
from src.services.deletion import Deletions
from src.services.processing_recovery import ProcessingRecovery
from src.services.thumbnails import CustomThumbnails
from src.services.uploads import SourceUploads
from src.services.videos import VideoService, utc_now


def create_app(
    settings: Settings | None = None,
    *,
    signing_keys: SigningKeys | None = None,
    clock: Callable[[], datetime] = utc_now,
    new_id: Callable[[], UUID] = uuid4,
    storage: Storage | None = None,
    launcher: JobLauncher | None = None,
) -> FastAPI:
    settings = settings or Settings()
    database = Database(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        await database.connect()
        try:
            yield
        finally:
            await database.close()

    app = FastAPI(
        title="Videos service",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.database = database
    app.state.videos = VideoService(database, clock=clock, new_id=new_id)
    app.state.settings = settings
    app.state.storage = storage or R2Storage(settings)
    app.state.thumbnails = CustomThumbnails(
        database, app.state.storage, settings, clock=clock, new_id=new_id
    )
    app.state.launcher = launcher or CloudRunJobLauncher(settings)
    app.state.processing_recovery = ProcessingRecovery(
        database, app.state.storage, app.state.launcher, clock=clock, new_id=new_id
    )
    app.state.deletions = Deletions(database, app.state.launcher, clock=clock, new_id=new_id)
    app.state.uploads = SourceUploads(
        database, app.state.storage, app.state.launcher, settings, clock=clock, new_id=new_id
    )
    app.state.authorization = Authorization(
        NeonIdentity(settings, signing_keys), NeonRoles(database, settings.auth_schema)
    )
    register_routers(app)
    return app
