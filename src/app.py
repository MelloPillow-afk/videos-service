"""ASGI application factory."""

from fastapi import FastAPI

from src.config import Settings
from src.core.generated.routers import register_routers
from src.extensions import lifespan
from src.providers.auth import DisabledAuth, NeonIdentity, SigningKeys


def create_app(
    settings: Settings | None = None, *, signing_keys: SigningKeys | None = None
) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="Videos service",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.authenticator = (
        DisabledAuth(settings.auth_disabled_subject)
        if settings.auth_disabled
        else NeonIdentity(settings, signing_keys)
    )
    register_routers(app)
    return app
