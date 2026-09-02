"""Celery worker + synchronous processing bridge.

`process_document_task` is the Celery entry point (production). `process_document_sync`
runs the same pipeline in-process for tests/dev. Both are idempotent thanks to the
single-active-job guard and stage-level re-creation of derived rows.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select

from app.core.tasks import celery_app
from app.db.base import AsyncSessionLocal
from app.models.document import Document, ProcessingJob
from app.services import repositories

logger = logging.getLogger(__name__)


async def process_document_sync(document_id: str) -> dict:
    """Run the pipeline in-process. Returns a small outcome dict."""
    from app.services.pipeline import run_pipeline

    doc_id = uuid.UUID(document_id)
    async with AsyncSessionLocal() as db:
        document = (
            await db.execute(select(Document).where(Document.id == doc_id))
        ).scalar_one_or_none()
        if document is None:
            logger.warning("process_document_sync: document %s not found", doc_id)
            return {"status": "not_found"}

        job = await repositories.get_active_job(db, document.id)
        if job is None:
            # No active job; create one so the pipeline bookkeeping works.
            job = ProcessingJob(
                document_id=document.id, user_id=document.user_id, status="pending"
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)

        outcome = await run_pipeline(db, document, job)
        return {"status": outcome.status, "stage": outcome.stage, "error": outcome.error}


@celery_app.task(name="app.worker.process_document_task", bind=True, max_retries=3)
def process_document_task(self, document_id: str) -> dict:
    """Celery task that processes a document asynchronously (production path)."""
    import asyncio

    result = asyncio.run(process_document_sync(document_id))

    if result.get("status") == "failed":
        # Allow limited retries for transient failures unless it's a hard error.
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=30)
    return result
