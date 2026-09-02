"""The document processing pipeline.

Runs the full sequence for a document:
validation -> inspection -> classification -> page extraction -> digital text / OCR ->
normalization -> sections -> tables -> structured extraction -> chunking -> embedding ->
vector storage -> metadata persistence -> completion.

Each stage tracks status in `processing_jobs.stages`. Stages are idempotent in the sense
that on retry we delete previously created derived rows for this document before
re-creating them, avoiding duplicate chunks/entities/tables.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import get_provider
from app.core.config import settings
from app.models.document import (
    Document,
    DocumentStatus,
    ExtractionResult,
    JobStatus,
    ProcessingJob,
    ReviewStatus,
)
from app.services import repositories
from app.services.chunker import chunk_pages
from app.services.classification import classify_document
from app.services.entities import EntityHit
from app.services.extraction import extract_entities, extract_structured
from app.services.image_preprocessing import open_image, preprocess_for_ocr
from app.services.ocr import OCRService
from app.services.storage import read_file
from app.services.summarization import summarize_document
from app.services.tables import DetectedTable, extract_tables_pdf
from app.services.text_extraction import (
    ExtractedPage,
    extract_docx,
    extract_pdf_digital,
    extract_plain,
    normalize_text,
)
from app.services.validation import (
    verify_page_count,
)

logger = logging.getLogger(__name__)

STAGE_ORDER = [
    "validating", "inspecting", "classifying", "pages", "text_extraction", "ocr",
    "normalization", "sections", "tables", "extraction", "chunking", "embedding",
    "persist", "completed",
]


class PipelineError(Exception):
    pass


@dataclass
class PipelineOutcome:
    status: str
    stage: str | None = None
    error: str | None = None


async def run_pipeline(
    db: AsyncSession,
    document: Document,
    job: ProcessingJob,
) -> PipelineOutcome:
    """Execute the pipeline for a document, mutating job stages as it goes.

    This is called by the worker (Celery) or, in tests, directly. It owns its own
    commit/flush lifecycle so a failure at any stage is persisted and retryable.
    """
    job.status = JobStatus.PROCESSING.value
    job.started_at = datetime.now(timezone.utc)
    job.attempts += 1

    document.status = DocumentStatus.PROCESSING.value
    await _set_stage(job, "queued", "completed")
    await db.commit()

    try:
        data = _load_bytes(document)
        ext = document.extension

        # --- validating ----------------------------------------------------
        await _set_stage(job, "validating", "processing")
        page_count = verify_page_count(data, ext)
        document.page_count = page_count
        await _set_stage(job, "validating", "completed")
        await db.commit()

        # --- inspecting / text extraction ----------------------------------
        await _set_stage(job, "inspecting", "processing")
        extraction, is_scanned = await _extract_document(data, ext)
        if not extraction.pages:
            raise PipelineError("Unable to extract any text from this document.")
        document.is_scanned = is_scanned
        document.text_method = extraction.method
        await _set_stage(job, "inspecting", "completed")
        await db.commit()

        # --- OCR if needed -------------------------------------------------
        await _set_stage(job, "ocr", "processing")
        ocr_map, ocr_conf, text_method = await _apply_ocr_if_needed(
            data, ext, extraction, is_scanned
        )
        document.text_method = text_method
        normalized_pages = [_normalise(p.text or ocr_map.get(p.number, "")) for p in extraction.pages]
        await _set_stage(job, "ocr", "completed")
        await db.commit()

        # --- persist pages + normalization/sections ------------------------
        await _set_stage(job, "pages", "processing")
        await repositories.delete_pages_for_document(db, document.id)
        await repositories.save_pages(db, document.id, extraction.pages, ocr_map=ocr_map, ocr_conf=ocr_conf)
        await _set_stage(job, "pages", "completed")
        await _set_stage(job, "normalization", "completed")
        await _set_stage(job, "sections", "completed")
        await db.commit()

        # --- classification ------------------------------------------------
        await _set_stage(job, "classifying", "processing")
        full_text = "\n\n".join(normalized_pages)
        doc_type, class_source = await classify_document(full_text)
        document.document_type = doc_type
        await _set_stage(job, "classifying", "completed")
        await db.commit()

        # --- tables --------------------------------------------------------
        await _set_stage(job, "tables", "processing")
        detected_tables = _detect_tables(data, ext, extraction.pages)
        await repositories.delete_tables_for_document(db, document.id)
        await repositories.save_tables(db, document.id, detected_tables)
        await _set_stage(job, "tables", "completed")
        await db.commit()

        # --- structured extraction ------------------------------------------
        await _set_stage(job, "extraction", "processing")
        extraction_result = await extract_structured(doc_type, normalized_pages, str(document.id))
        await repositories.delete_extraction_for_document(db, document.id)
        needs_review = extraction_result["confidence"] < 0.6 or bool(extraction_result["warnings"] and len(extraction_result["warnings"]) > 2)
        await repositories.save_extraction(
            db,
            ExtractionResult(
                document_id=document.id,
                schema_type=doc_type,
                raw_data=extraction_result["data"],
                corrected_data={},
                confidence=extraction_result["confidence"],
                needs_review=needs_review,
                review_status=ReviewStatus.PENDING.value if needs_review else ReviewStatus.NOT_REQUIRED.value,
                source_refs=extraction_result["source_refs"],
            ),
        )
        document.review_status = ReviewStatus.PENDING.value if needs_review else ReviewStatus.NOT_REQUIRED.value
        await _set_stage(job, "extraction", "completed")
        await db.commit()

        # --- entities -------------------------------------------------------
        entity_raw = await extract_entities(full_text)
        hits = [EntityHit(**e) for e in entity_raw["entities"]]
        await repositories.delete_entities_for_document(db, document.id)
        await repositories.save_entities(db, document.id, hits)

        # --- summary --------------------------------------------------------
        document.summary = await summarize_document(full_text)
        document.summary_is_generated = True

        # --- chunking -------------------------------------------------------
        await _set_stage(job, "chunking", "processing")
        chunks = chunk_pages(normalized_pages)
        await _delete_chunks_and_vectors(db, document.id)
        await _set_stage(job, "chunking", "completed")
        await db.commit()

        # --- embedding + vector storage -------------------------------------
        await _set_stage(job, "embedding", "processing")
        texts = [c.text for c in chunks]
        embeddings = await _embed(texts)
        count = await repositories.save_chunks(db, document.id, document.user_id, chunks, embeddings)
        await _set_stage(job, "embedding", "completed")
        await db.commit()

        # --- persist / completion --------------------------------------------
        await _set_stage(job, "persist", "processing")
        document.status = DocumentStatus.COMPLETED.value
        document.processed_at = datetime.now(timezone.utc)
        document.processing_meta = {
            "chunk_count": count,
            "table_count": len(detected_tables),
            "entity_count": len(hits),
            "classification_source": class_source,
            "text_method": text_method,
        }
        job.status = JobStatus.COMPLETED.value
        job.current_stage = "completed"
        job.finished_at = datetime.now(timezone.utc)
        await _set_stage(job, "persist", "completed")
        await _set_stage(job, "completed", "completed")
        await db.commit()
        return PipelineOutcome(status="completed", stage="completed")

    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed for document %s", document.id)
        await _mark_failed(db, document, job, exc)
        return PipelineOutcome(status=JobStatus.FAILED.value, stage=job.current_stage, error=str(exc)[:2000])


# ------------------------------------------------------------------------- helpers


def _load_bytes(document: Document) -> bytes:
    try:
        return read_file(document.storage_key)
    except Exception as exc:
        raise PipelineError(f"Unable to read stored file: {exc}") from exc


async def _extract_document(data: bytes, ext: str):
    """Return (ExtractionResult, is_scanned_bool)."""
    if ext == "pdf":
        result = extract_pdf_digital(data)
        return result, result.method in ("ocr", "mixed")
    if ext in {"docx", "doc"}:
        try:
            result = extract_docx(data)
        except Exception:
            if ext == "doc":
                # .doc is hard; attempt text fallback via simple extraction.
                text = _extract_doc_binary(data)
                return extract_plain(text), False
            raise
        return result, False
    if ext in {"txt", "md", "rtf"}:
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = data.decode("latin-1", errors="replace")
        return extract_plain(text), False
    if ext in {"png", "jpg", "jpeg", "tiff", "tif", "bmp", "gif", "webp"}:
        # Image: no digital text; route straight to OCR.
        return ExtractionResult(pages=[ExtractedPage(number=1, text="")], method="none"), True
    raise PipelineError(f"Unsupported file extension: {ext}")


def _extract_doc_binary(data: bytes) -> str:
    # Minimal text extraction for legacy .doc (best effort).
    text = data.decode("latin-1", errors="ignore")
    # Remove non-printable noise.
    import re

    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    return text[:50000]


async def _apply_ocr_if_needed(data, ext, extraction, is_scanned):
    """Apply OCR to scanned/image documents. Returns (ocr_map, conf_map, text_method)."""
    ocr_map: dict[int, str] = {}
    conf_map: dict[int, float] = {}
    if not is_scanned:
        return ocr_map, conf_map, extraction.method if extraction.pages else "none"

    service = OCRService()
    # For PDFs, render pages; for images, open directly.
    pdf_doc = None
    if ext == "pdf":
        import fitz

        pdf_doc = fitz.open(stream=data, filetype="pdf")

    for p in extraction.pages:
        try:
            img = _render_or_open(p.number, pdf_doc, data, ext)
            if img is not None:
                prepped = preprocess_for_ocr(img, render_dpi=settings.ocr_render_dpi)
                res = service.ocr_image(prepped)
                ocr_map[p.number] = res.text
                conf_map[p.number] = res.confidence
                p.text = res.text  # overwrite page text with OCR result
        except Exception as exc:  # noqa: BLE001
            logger.warning("OCR failed on page %s: %s", p.number, exc)
            # Leave page text as-is; OCR failure shouldn't abort whole doc.

    if pdf_doc is not None:
        pdf_doc.close()

    if ocr_map:
        return ocr_map, conf_map, "ocr"
    return ocr_map, conf_map, "none"


def _render_or_open(page_number, pdf_doc, data, ext):
    from PIL import Image
    import io

    if pdf_doc is not None:
        pix = pdf_doc.load_page(page_number - 1).get_pixmap(dpi=settings.ocr_render_dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img
    if ext in {"png", "jpg", "jpeg", "tiff", "tif", "bmp", "gif", "webp"}:
        return open_image(data)
    return None


def _normalise(text: str) -> str:
    return normalize_text(text)


def _detect_tables(data: bytes, ext: str, pages: list) -> list[DetectedTable]:
    if ext != "pdf":
        return []
    try:
        return extract_tables_pdf(data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Table extraction failed: %s", exc)
        return []


async def _embed(texts: list[str]):
    try:
        provider = get_provider()
        return await provider.embed_texts(texts)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Embedding failed (%s); storing chunks without vectors", exc)
        return []


async def _delete_chunks_and_vectors(db: AsyncSession, document_id: uuid.UUID) -> None:
    # Delete chunk rows; vector data is removed with them (column lives on the same row).
    await repositories.delete_chunks_for_document(db, document_id)


async def _set_stage(job: ProcessingJob, stage: str, status: str, error: str | None = None) -> None:
    job.stages = dict(job.stages or {})
    job.stages[stage] = {"status": status, "error": error}
    job.current_stage = stage


async def _mark_failed(db: AsyncSession, document: Document, job: ProcessingJob, exc: Exception) -> None:
    document.status = DocumentStatus.FAILED.value
    document.error_message = str(exc)[:2000]
    job.status = JobStatus.FAILED.value
    job.error = str(exc)[:2000]
    job.finished_at = datetime.now(timezone.utc)
    await _set_stage(job, job.current_stage or "unknown", "failed", str(exc)[:500])
    job.stages = dict(job.stages or {})
    job.stages[job.current_stage or "unknown"] = {"status": "failed", "error": str(exc)[:500]}
    await db.commit()
