# src/api/main.py
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.auth.rbac import scan_permission_declarations
from api.config.logging import configure_logging
from api.config.settings import Settings, get_settings
from api.db.redis import build_redis
from api.db.session import build_engine, build_session_factory
from api.errors import APIError
from api.middleware.request_id import RequestIDMiddleware
from api.routes.v1 import auth, documents, health, me, members, orgs
from shared.storage.r2 import R2Storage

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

    # Storage is optional at boot and required at the document routes. An API that
    # refuses to start without a bucket takes authentication, membership and every
    # other phase down with it on a machine that has no R2 account; a document upload
    # that answers 503 with a named reason does not.
    if settings.storage_bucket and settings.storage_endpoint_url:
        app.state.storage = R2Storage.from_settings(settings)
    else:
        app.state.storage = None
        logger.warning("storage.unconfigured", detail="document routes will answer 503")

    logger.info("api.startup", environment=settings.environment)
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()
        logger.info("api.shutdown")


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Map every domain error to a response, in one place.

    Registered for ``APIError``, which ``AuthError`` (Phase 4) and the document errors
    (Phase 6) both inherit — Starlette resolves a handler by walking the exception's
    MRO, so one registration covers every phase, including ones not written yet.

    The client gets ``exc.detail``; the log gets ``exc.reason``. Keeping the two apart
    is what lets every credential failure return one uninformative body while the log
    still says which check failed.
    """
    logger.info(
        "api.request_rejected",
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
    app.add_exception_handler(APIError, api_error_handler)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(me.router, prefix="/api/v1")
    app.include_router(orgs.creation_router, prefix="/api/v1")
    app.include_router(orgs.router, prefix="/api/v1")
    app.include_router(members.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")

    # Default deny, decided once at boot: every organization-scoped route is checked
    # for a declared permission, and the ones without are logged as errors. The
    # request-time guard on the organization routers refuses them anyway — this makes
    # the omission visible at startup rather than in a support ticket.
    scan_permission_declarations(app)
    return app


app = create_app()
