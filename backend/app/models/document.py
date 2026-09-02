"""Document, page, chunk, entity, table, extraction and job models.

These tables are the relational + vector backbone of the platform. Ownership scoping is
enforced by a `user_id` column on every document-owned row so user isolation is
enforceable at query time.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict, MutableList

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.vector import Vector as pgvector_Vector
from app.core.config import settings


class DocumentStatus(str, Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    DELETED = "deleted"


class ProcessingStage(str, Enum):
    """Named pipeline stages used for progress reporting."""

    QUEUED = "queued"
    VALIDATING = "validating"
    INSPECTING = "inspecting"
    CLASSIFYING = "classifying"
    PAGES = "pages"
    TEXT_EXTRACTION = "text_extraction"
    OCR = "ocr"
    NORMALIZATION = "normalization"
    SECTIONS = "sections"
    TABLES = "tables"
    EXTRACTION = "extraction"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    PERSIST = "persist"
    COMPLETED = "completed"
    FAILED = "failed"


class EntityType(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    DATE = "DATE"
    MONEY = "MONEY"
    LOCATION = "LOCATION"
    OTHER = "OTHER"


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


class ReviewStatus(str, Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    REVIEWED = "reviewed"


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single uploaded source document owned by a user."""

    __tablename__ = "documents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    #: Safely generated storage key; never a user-supplied path.
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    extension: Mapped[str] = mapped_column(String(16), nullable=False)

    #: Detected document category (invoice, receipt, ...). "unknown" when undetermined.
    document_type: Mapped[str] = mapped_column(String(64), default="unknown", index=True)
    status: Mapped[str] = mapped_column(String(32), default=DocumentStatus.UPLOADED.value)
    review_status: Mapped[str] = mapped_column(ReviewStatus.NOT_REQUIRED.value, default=ReviewStatus.NOT_REQUIRED.value)

    page_count: Mapped[int] = mapped_column(Integer, default=0)
    #: Whether the source had extractable text (digital) or needed OCR.
    is_scanned: Mapped[bool] = mapped_column(default=False)
    #: Overall text-extraction mechanism used ("digital" | "ocr" | "mixed" | "none").
    text_method: Mapped[str] = mapped_column(String(32), nullable=True)

    title: Mapped[str] = mapped_column(String(512), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    summary_is_generated: Mapped[bool] = mapped_column(default=False)

    #: JSON metrics & processing metadata (per-stage status, timing, errors) — not user data leakage.
    processing_meta: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="documents")
    pages = relationship(
        "DocumentPage",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentPage.page_number",
    )
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    entities = relationship(
        "DocumentEntity",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    tables = relationship(
        "DocumentTable",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    extractions = relationship(
        "ExtractionResult",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    jobs = relationship(
        "ProcessingJob",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    conversations = relationship(
        "Conversation",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentPage(UUIDPrimaryKeyMixin, Base):
    """A single page of a document, with its extracted/normalized text."""

    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number", name="uq_page_doc_num"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, default="")
    #: raw OCR text (if OCR was used) retained for auditing/comparison.
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    section: Mapped[str] = mapped_column(String(256), nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    ocr_confidence: Mapped[float] = mapped_column(default=0.0)
    #: rendered thumbnail/preview key (optional)
    preview_key: Mapped[str] = mapped_column(String(512), nullable=True)

    document = relationship("Document", back_populates="pages")


class DocumentChunk(UUIDPrimaryKeyMixin, Base):
    """A semantic text chunk of a document with a stored pgvector embedding.

    The embedding column lives in this table (with a vector index defined in migrations)
    rather than a separate table so ownership filtering can be applied in one join.
    """

    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(256), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    #: The vector is managed by pgvector; see models/vector.py for the column class.
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", MutableDict.as_mutable(JSON), default=dict
    )
    #: pgvector embedding for this chunk (managed in migrations).
    embedding: Mapped[Any | None] = mapped_column(
        "embedding", pgvector_Vector(settings.embedding_dimensions), nullable=True
    )

    document = relationship("Document", back_populates="chunks")
    UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_index")


class DocumentEntity(UUIDPrimaryKeyMixin, Base):
    """An entity (person, org, date, ...) detected in a document."""

    __tablename__ = "document_entities"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(default=0.0)
    page_number: Mapped[int] = mapped_column(Integer, nullable=True)
    occurrences: Mapped[int] = mapped_column(Integer, default=1)

    document = relationship("Document", back_populates="entities")


class DocumentTable(UUIDPrimaryKeyMixin, Base):
    """A detected table with its normalized row/column structure."""

    __tablename__ = "document_tables"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    table_index: Mapped[int] = mapped_column(Integer, default=0)
    headers: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    rows: Mapped[list[list[str]]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    confidence: Mapped[float] = mapped_column(default=0.0)
    source: Mapped[str] = mapped_column(String(32), nullable=True)  # "pdf" | "ocr" | "llm"

    document = relationship("Document", back_populates="tables")


class ExtractionResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Structured extraction for a document type.

    Raw model output is stored in `raw_data`; human-corrected values are stored in
    `corrected_data` with provenance in `corrections` and `reviewed_by_user_id` so we
    preserve traceability between machine output and human review.
    """

    __tablename__ = "extraction_results"
    __table_args__ = (UniqueConstraint("document_id", "schema_type", name="uq_extraction_doc_schema"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    schema_type: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Raw LLM/extraction output (any shape). NEVER displayed as authoritative.
    raw_data: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    #: Human-reviewed/corrected values; separate from raw output.
    corrected_data: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    #: Whether the extraction is considered low-confidence / needs review.
    confidence: Mapped[float] = mapped_column(default=0.0)
    needs_review: Mapped[bool] = mapped_column(default=False)
    review_status: Mapped[str] = mapped_column(ReviewStatus.NOT_REQUIRED.value, default=ReviewStatus.NOT_REQUIRED.value)
    reviewed_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    #: List of {field, from_val, to_val} human corrections for audit.
    corrections: Mapped[list[dict[str, Any]]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    #: Source/page references for extracted fields.
    source_refs: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)

    document = relationship("Document", back_populates="extractions")


class ProcessingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A unit of background work that runs the document pipeline."""

    __tablename__ = "processing_jobs"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.PENDING.value, index=True)
    current_stage: Mapped[str] = mapped_column(String(32), nullable=True)
    #: Ordered list of stage -> status for progress reporting.
    stages: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Optional ID used to make job scheduling idempotent (one active job per document).
    celery_task_id: Mapped[str] = mapped_column(String(255), nullable=True)

    document = relationship("Document", back_populates="jobs")


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Immutable audit trail of security-relevant actions."""

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSON), default=dict)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False
    )

    user = relationship("User", back_populates="audit_logs")
