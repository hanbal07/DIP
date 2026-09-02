"""FastAPI application factory for Document Intelligence Platform."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, chat, documents, health, search
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.rate_limit import RateLimitMiddleware
from app.services.storage import ensure_dirs
from app.core.tasks import celery_app

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    ensure_dirs()
    logger.info(
        "Starting %s in %s environment (ai=%s)",
        settings.app_name,
        settings.environment,
        settings.ai_provider,
    )
    yield
    # Graceful shutdown notes for Celery/engine.
    from app.db.base import engine

    await engine.dispose()


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "End-to-end AI document processing platform: upload, validate, classify, "
            "OCR, extract structured info, embed, and chat over documents with RAG."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)

    api_prefix = settings.api_prefix
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(documents.router, prefix=api_prefix)
    app.include_router(search.router, prefix=api_prefix)
    app.include_router(chat.router, prefix=api_prefix)
    app.include_router(health.router)

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {"name": settings.app_name, "docs": "/docs", "health": "/health"}

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request, exc):  # pragma: no cover
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()
