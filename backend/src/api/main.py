# src/api/main.py
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.auth.exceptions import AuthError
from api.config.logging import configure_logging
from api.config.settings import Settings, get_settings
from api.db.redis import build_redis
from api.db.session import build_engine, build_session_factory
from api.middleware.request_id import RequestIDMiddleware
from api.routes.v1 import auth, health, me

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings

    engine = build_engine(settings)
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)

    # Opened once, not per request: every authenticated request checks the revocation
    # deny-list, so this connection pool is on the critical path of the whole API.
    app.state.redis = build_redis(settings)

    logger.info("api.startup", environment=settings.environment)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()
        logger.info("api.shutdown")


async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    """Map domain auth errors to responses, in one place.

    The client gets ``exc.detail``; the log gets ``exc.reason``. Keeping the two apart
    is what lets every credential failure return one uninformative body while the log
    still says which check failed.
    """
    logger.info(
        "auth.request_rejected",
        reason=exc.reason,
        status_code=exc.status_code,
        path=request.url.path,
    )
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )


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
    app.add_exception_handler(AuthError, auth_error_handler)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(me.router, prefix="/api/v1")
    return app


app = create_app()
