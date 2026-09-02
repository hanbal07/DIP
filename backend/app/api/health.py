"""Health and diagnostics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import ai_mode
from app.core.config import settings
from app.db.base import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    db_status = "unavailable"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        pass

    redis_status = "unknown"
    if settings.environment in {"test", "development"}:
        redis_status = "mock"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "1.0.0",
        "environment": settings.environment,
        "database": db_status,
        "redis": redis_status,
        "ai_mode": ai_mode(),
    }
