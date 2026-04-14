import asyncio
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import engine
from app.models import models  # noqa: F401  - ensure models are imported for metadata


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler: creates upload directory structure on startup,
    starts the IMAP polling task (if enabled) and disposes the DB engine on shutdown."""
    # Create upload directory tree
    #   uploads/
    #     avatars/          ← one file per user, named {user_id}.{ext}  (served as public static)
    #     attachments/      ← sharded: attachments/{xx}/{uuid}.{ext}   (served via auth endpoint)
    for subdir in ("avatars", "attachments"):
        os.makedirs(os.path.join(settings.UPLOAD_DIR, subdir), exist_ok=True)

    # Start IMAP email-ingestion poller if configured
    imap_task: asyncio.Task[None] | None = None
    if settings.IMAP_ENABLED:
        from app.services import imap_poller  # local import keeps startup fast when disabled
        imap_task = asyncio.create_task(imap_poller.run_forever(), name="imap-poller")

    yield

    # Cleanup on shutdown
    if imap_task is not None:
        imap_task.cancel()
        try:
            await imap_task
        except asyncio.CancelledError:
            pass

    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with middleware, routes and static file serving."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # S-5: rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],  # S-9: explicit allowlist
        allow_headers=["Authorization", "Content-Type"],  # S-9: explicit allowlist
    )

    app.include_router(api_router)

    # Serve only avatar images as public static files.
    # Ticket attachments are served via the authenticated
    # GET /api/v1/tickets/{id}/attachments/{id}/download endpoint (A-5).
    avatars_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    if os.path.exists(avatars_dir):
        app.mount("/uploads/avatars", StaticFiles(directory=avatars_dir), name="avatars")

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health-check endpoint — returns the current application status and version."""
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
