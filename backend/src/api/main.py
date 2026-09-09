# src/api/main.py
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from api.config.logging import configure_logging
from api.config.settings import Settings, get_settings
from api.middleware.request_id import RequestIDMiddleware
from api.routes.v1 import health

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    logger.info("api.startup", environment=settings.environment)
    yield
    logger.info("api.shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="Enterprise Intelligence Knowledge Base",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )
    app.state.settings = settings
    app.add_middleware(RequestIDMiddleware)
    app.include_router(health.router, prefix="/api/v1")
    return app


app = create_app()
