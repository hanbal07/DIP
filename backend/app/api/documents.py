"""Document management endpoints: upload, list, get, delete, status, data."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.tasks import run_sync, schedule_processing
from app.db.base import get_db
from app.models.document import (
    Document,
    DocumentStatus,
    JobStatus,
    ProcessingJob,
    ReviewStatus,
    ExtractionResult,
)
from app.models.user import User
from app.schemas.document import (
    CorrectionRequest,
    DocumentDetail,
    DocumentList,
    DocumentListItem,
    EntityRead,
    ExtractionRead,
    JobRead,
    PageRead,
    TableRead,
    TaskResponse,
)
from app.services import repositories
from app.services.storage import delete_file, save_upload
from app.services.validation import validate_upload

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=TaskResponse, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Upload a document, validate it, and enqueue background processing.

    Returns 202 Accepted with the document id and processing job id.
    """
    original = file.filename or "upload"
    # Read up to a small bound to validate size cheaply; full read happens in storage.
    # We validate size in save_upload (streaming) and MIME/extension here.
    size_guess = 0

    # Stream to storage first (validates size while writing).
    try:
        storage_key, display_name, size = await save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Validate MIME/extension (post-write; we still have bytes on disk but validate via
    # metadata). Early validation avoids writing files we reject, but safe storage already
    # guards dangerous extensions.
    try:
        validation = validate_upload(display_name, file.content_type, size)
    except Exception as exc:
        from app.services.storage import delete_file

        delete_file(storage_key)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document = Document(
        user_id=current_user.id,
        filename=display_name,
        storage_key=storage_key,
        content_type=validation.content_type,
        file_size=size,
        extension=validation.extension or "",
        status=DocumentStatus.PENDING.value,
    )
    db.add(document)
    await db.flush()

    # Create a processing job (idempotency: one active job per document, fresh document).
    job = ProcessingJob(document_id=document.id, user_id=current_user.id, status=JobStatus.PENDING.value)
    job.stages = {"queued": {"status": "processing"}}
    db.add(job)
    await db.commit()
    await db.refresh(document)
    await db.refresh(job)

    await repositories.write_audit(
        db, current_user.id, "document.upload", "document", str(document.id),
        {"filename": display_name, "size": size},
    )

    # Schedule background processing.
    task_id = schedule_processing(document.id)
    job.celery_task_id = task_id
    await db.commit()

    if settings.environment in {"test", "development"}:
        # In dev/test we may still use the sync path if requested; default is async.
        pass

    return TaskResponse(document_id=document.id, job_id=job.id, status=job.status)


@router.get("", response_model=DocumentList)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    document_type: str | None = Query(None),
    search: str | None = Query(None),
    review_status: str | None = Query(None),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentList:
    items, total = await repositories.list_documents(
        db, current_user.id, page=page, page_size=page_size, status=status,
        document_type=document_type, search=search, review_status=review_status,
        sort=sort, order=order,
    )
    return DocumentList(
        items=[DocumentListItem.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document:
    doc = await repositories.get_owned_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{document_id}/status", response_model=DocumentDetail)
async def get_document_status(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Document:
    doc = await repositories.get_owned_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=200)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    doc = await repositories.get_owned_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await repositories.delete_document_tree(db, doc)
    await repositories.write_audit(
        db, current_user.id, "document.delete", "document", str(document_id)
    )
    return {"message": "Document deleted", "document_id": str(document_id)}


@router.get("/{document_id}/jobs", response_model=list[JobRead])
async def list_document_jobs(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProcessingJob]:
    doc = await repositories.get_owned_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return await repositories.get_jobs_for_document(db, document_id, current_user.id)


# --------------------------------------------------------------------- extracted data


@router.get("/{document_id}/extraction", response_model=ExtractionRead)
async def get_extraction(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractionResult:
    doc = await repositories.get_owned_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    ext = await repositories.get_extraction(db, document_id, doc.document_type)
    if ext is None:
        raise HTTPException(status_code=404, detail="No extraction available for this document")
    return ext


@router.put("/{document_id}/extraction/review", response_model=ExtractionRead)
async def review_extraction(
    document_id: uuid.UUID,
    payload: CorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExtractionResult:
    """Human review: store corrected values separately from raw model output."""
    doc = await repositories.get_owned_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    ext = await repositories.get_extraction(db, document_id, doc.document_type)
    if ext is None:
        raise HTTPException(status_code=404, detail="No extraction available for this document")

    from datetime import datetime, timezone

    corrections_log: list[dict] = list(ext.corrections or [])
    corrected = dict(ext.corrected_data or {})
    for item in payload.corrections:
        if item.field in ext.raw_data or item.field in (ext.corrected_data or {}):
            prev = corrected.get(item.field, ext.raw_data.get(item.field))
            corrected[item.field] = item.value
            corrections_log.append(
                {"field": item.field, "from": prev, "to": item.value, "by": str(current_user.id)}
            )

    ext.corrected_data = corrected
    ext.corrections = corrections_log
    ext.review_status = ReviewStatus.REVIEWED.value
    ext.reviewed_by_user_id = current_user.id
    ext.reviewed_at = datetime.now(timezone.utc)
    ext.needs_review = False
    doc.review_status = ReviewStatus.REVIEWED.value

    await repositories.write_audit(
        db, current_user.id, "extraction.review", "document", str(document_id),
        {"fields": [c.field for c in payload.corrections]},
    )
    await db.commit()
    await db.refresh(ext)
    return ext


# ---------------------------------------------------------------------- pages/entities


@router.get("/{document_id}/pages", response_model=list[PageRead])
async def get_pages(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await repositories.get_owned_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return await repositories.get_pages(db, document_id)


@router.get("/{document_id}/entities", response_model=list[EntityRead])
async def get_entities(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await repositories.get_owned_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return await repositories.get_entities(db, document_id)


@router.get("/{document_id}/tables", response_model=list[TableRead])
async def get_tables(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await repositories.get_owned_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return await repositories.get_tables(db, document_id)


# ----------------------------------------------------------------------------- export


@router.post("/{document_id}/export/csv")
async def export_tables_csv(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    doc = await repositories.get_owned_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    tables = await repositories.get_tables(db, document_id)
    if not tables:
        raise HTTPException(status_code=404, detail="No tables to export")

    buf = io.StringIO()
    writer = csv.writer(buf)
    for t in tables:
        writer.writerow([f"Table {t.table_index} (page {t.page_number})"])
        if t.headers:
            writer.writerow(t.headers)
        for row in t.rows:
            writer.writerow(row)
        writer.writerow([])
    buf.seek(0)

    filename = f"{doc.filename.rsplit('.',1)[0]}_tables.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
