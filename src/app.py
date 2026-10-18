"""ASGI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.clients.auth import DisabledAuth, NeonIdentity, SigningKeys
from src.config import Settings
from src.core.generated.routers import register_routers
from src.extensions import lifespan


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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Location"],
    )
    app.state.authenticator = (
        DisabledAuth(settings.auth_disabled_subject)
        if settings.auth_disabled
        else NeonIdentity(settings, signing_keys)
    )
    register_routers(app)
    return app
