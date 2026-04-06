import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import engine
from app.models import models  # noqa: F401  - ensure models are imported for metadata


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler: creates upload directory structure on startup and disposes the DB engine on shutdown."""
    # Create upload directory tree
    #   uploads/
    #     avatars/          ← one file per user, named {user_id}.{ext}
    #     attachments/      ← sharded: attachments/{xx}/{uuid}.{ext}
    for subdir in ("avatars", "attachments"):
        os.makedirs(os.path.join(settings.UPLOAD_DIR, subdir), exist_ok=True)
    yield
    # Cleanup on shutdown
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    # Serve uploaded files
    if os.path.exists(settings.UPLOAD_DIR):
        app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health-check endpoint — returns the current application status and version."""
        return {"status": "ok", "version": settings.APP_VERSION}

    return app


app = create_app()
