"""Task scheduling abstraction.

In production, document processing runs in a Celery worker backed by Redis. In tests and
simple development (or when Celery/Redis is unavailable), we provide a synchronous
`run_sync` that executes the job immediately — used by the test suite and the mock path.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from celery import Celery  # type: ignore

    celery_app = Celery(
        "document_intelligence",
        broker=settings.redis_url,
        backend=settings.redis_url,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
    )
    celery_app.conf.task_routes = {"app.worker.process_document_task": {"queue": settings.task_queue_name}}
    HAS_CELERY = True
except Exception as exc:  # pragma: no cover
    logger.warning("Celery unavailable (%s); processing will use synchronous path.", exc)
    celery_app = None
    HAS_CELERY = False


def schedule_processing(document_id: uuid.UUID) -> str | None:
    """Enqueue a document for processing. Returns a task id (or None for sync path).

    Uses `apply_async` with a dedupe guard: the API layer already ensures a single active
    job per document, so a duplicate schedule is a no-op.
    """
    from app.worker import process_document_task

    if HAS_CELERY and settings.environment == "production":
        result = process_document_task.apply_async(
            args=[str(document_id)], queue=settings.task_queue_name
        )
        return result.id
    return None


def run_sync(document_id: uuid.UUID) -> None:
    """Run the pipeline synchronously in the current process (for tests/dev)."""
    from app.worker import process_document_sync

    try:
        asyncio.get_event_loop()
    except RuntimeError:
        pass
    result = asyncio.run(process_document_sync(str(document_id)))
    return result
