"""Pydantic schemas for documents, processing, extraction and related data."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- documents


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: str
    file_size: int
    document_type: str
    status: str
    review_status: str
    page_count: int
    is_scanned: bool
    text_method: str | None
    title: str | None
    created_at: datetime
    processed_at: datetime | None
    error_message: str | None


class DocumentDetail(DocumentListItem):
    summary: str | None
    summary_is_generated: bool
    processing_meta: dict[str, Any] = Field(default_factory=dict)


class DocumentList(BaseModel):
    items: list[DocumentListItem]
    total: int
    page: int
    page_size: int


class TaskResponse(BaseModel):
    document_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    message: str = "Accepted"


# --------------------------------------------------------------------- processing job

class JobStageInfo(BaseModel):
    stage: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    current_stage: str | None
    stages: dict[str, Any]
    attempts: int
    max_attempts: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


# --------------------------------------------------------------------------- pages

class PageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_number: int
    text: str
    section: str | None
    char_count: int
    ocr_confidence: float
    has_preview: bool = False


# ------------------------------------------------------------------------- entities

class EntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    value: str
    confidence: float
    page_number: int | None
    occurrences: int


# --------------------------------------------------------------------------- tables

class TableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_number: int
    table_index: int
    headers: list[str]
    rows: list[list[str]]
    confidence: float
    source: str | None


# ---------------------------------------------------------------- extraction results

class FieldRef(BaseModel):
    field: str
    page_number: int | None = None
    chunk_id: str | None = None
    snippet: str | None = None


class ExtractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    schema_type: str
    raw_data: dict[str, Any]
    corrected_data: dict[str, Any]
    confidence: float
    needs_review: bool
    review_status: str
    corrections: list[dict[str, Any]]
    source_refs: dict[str, Any]
    reviewed_at: datetime | None


class CorrectionItem(BaseModel):
    field: str
    value: Any = None


class CorrectionRequest(BaseModel):
    corrections: list[CorrectionItem]


# ------------------------------------------------------------------------------ search

class SearchHit(BaseModel):
    document_id: uuid.UUID
    document_filename: str
    page_number: int
    chunk_index: int
    section: str | None
    text: str
    score: float
    snippet: str


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]
    total: int


# -------------------------------------------------------------------------------- chat

class CitationOut(BaseModel):
    document_id: uuid.UUID
    document_filename: str
    page_number: int
    snippet: str
    score: float = 0.0


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] | None = Field(default=None, max_length=20)


class ChatResponse(BaseModel):
    answer: str
    conversation_id: uuid.UUID
    question: str
    citations: list[CitationOut]
    has_sufficient_evidence: bool
    used_document_ids: list[uuid.UUID] = Field(default_factory=list)
    model: str | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    citations: list[dict[str, Any]] = Field(default_factory=list)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID | None
    title: str | None
    created_at: datetime
    updated_at: datetime


# ----------------------------------------------------------------------------- misc

class ExportResponse(BaseModel):
    filename: str
    url: str
    content_type: str


class HealthOut(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    redis: str
    ai_mode: str
