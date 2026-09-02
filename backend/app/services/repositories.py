"""Data-access helpers for documents and related tables (ownership-scoped)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.document import (
    AuditLog,
    Document,
    DocumentChunk,
    DocumentEntity,
    DocumentPage,
    DocumentTable,
    ExtractionResult,
    ProcessingJob,
)
from app.models.user import User


# ----------------------------------------------------------------------------- documents


async def get_owned_document(
    session: AsyncSession, user_id: uuid.UUID, document_id: uuid.UUID
) -> Document | None:
    stmt = select(Document).where(
        Document.id == document_id, Document.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_documents(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    document_type: str | None = None,
    search: str | None = None,
    review_status: str | None = None,
    sort: str = "created_at",
    order: str = "desc",
) -> tuple[list[Document], int]:
    conditions = [Document.user_id == user_id]
    if status:
        conditions.append(Document.status == status)
    if document_type:
        conditions.append(Document.document_type == document_type)
    if search:
        conditions.append(Document.filename.ilike(f"%{search}%"))
    if review_status:
        conditions.append(Document.review_status == review_status)

    total = (
        await session.execute(select(func.count()).select_from(Document).where(*conditions))
    ).scalar_one()

    sort_col = {
        "created_at": Document.created_at,
        "filename": Document.filename,
        "document_type": Document.document_type,
        "status": Document.status,
        "file_size": Document.file_size,
    }.get(sort, Document.created_at)

    order_col = sort_col.desc() if order == "desc" else sort_col.asc()
    stmt = (
        select(Document)
        .where(*conditions)
        .order_by(order_col)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await session.execute(stmt)).scalars().all()
    return list(items), total


async def delete_document_tree(session: AsyncSession, document: Document) -> None:
    """Delete a document and all associated data + file.

    Relational children are removed via ORM cascade; pgvector chunks are handled by the
    caller (file deletion). Conversations & citations cascade through the relationship.
    """
    # Remove the stored file first (outside DB).
    from app.services.storage import delete_file

    try:
        delete_file(document.storage_key)
    except Exception:
        pass

    # Delete conversations explicitly to also clean citations via cascade.
    conv_stmt = select(Conversation.id).where(Conversation.document_id == document.id)
    conv_ids = (await session.execute(conv_stmt)).scalars().all()
    for cid in conv_ids:
        await session.execute(
            Message.__table__.delete().where(Message.conversation_id == cid)
        )
    await session.execute(Conversation.__table__.delete().where(Conversation.document_id == document.id))

    # ORM cascade deletes pages, chunks, entities, tables, extractions, jobs.
    await session.delete(document)
    await session.commit()


# ------------------------------------------------------------------------------ pages


async def save_pages(
    session: AsyncSession,
    document_id: uuid.UUID,
    pages: Sequence[Any],
    *,
    ocr_map: dict[int, Any] | None = None,
    ocr_conf: dict[int, float] | None = None,
) -> None:
    ocr_map = ocr_map or {}
    ocr_conf = ocr_conf or {}
    for p in pages:
        page = DocumentPage(
            document_id=document_id,
            page_number=p.number,
            text=p.text,
            ocr_text=ocr_map.get(p.number, ""),
            ocr_confidence=ocr_conf.get(p.number, 0.0),
            char_count=len(p.text),
        )
        session.add(page)
    await session.flush()


async def get_pages(session: AsyncSession, document_id: uuid.UUID) -> list[DocumentPage]:
    stmt = (
        select(DocumentPage)
        .where(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
    )
    return list((await session.execute(stmt)).scalars().all())


# ----------------------------------------------------------------------------- chunks


async def delete_chunks_for_document(session: AsyncSession, document_id: uuid.UUID) -> None:
    await session.execute(DocumentChunk.__table__.delete().where(DocumentChunk.document_id == document_id))
    await session.flush()


async def delete_pages_for_document(session: AsyncSession, document_id: uuid.UUID) -> None:
    await session.execute(DocumentPage.__table__.delete().where(DocumentPage.document_id == document_id))
    await session.flush()


async def delete_tables_for_document(session: AsyncSession, document_id: uuid.UUID) -> None:
    await session.execute(DocumentTable.__table__.delete().where(DocumentTable.document_id == document_id))
    await session.flush()


async def delete_entities_for_document(session: AsyncSession, document_id: uuid.UUID) -> None:
    await session.execute(DocumentEntity.__table__.delete().where(DocumentEntity.document_id == document_id))
    await session.flush()


async def delete_extraction_for_document(session: AsyncSession, document_id: uuid.UUID) -> None:
    await session.execute(ExtractionResult.__table__.delete().where(ExtractionResult.document_id == document_id))
    await session.flush()


async def save_chunks(session: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID,
                     chunks: Sequence[Any], embeddings: list[list[float]] | None = None) -> int:
    """Persist chunks (+ optional embeddings). Returns count saved."""
    count = 0
    for i, chunk in enumerate(chunks):
        row = DocumentChunk(
            document_id=document_id,
            user_id=user_id,
            page_number=chunk.page_number,
            chunk_index=i,
            section=chunk.section,
            text=chunk.text,
            char_count=len(chunk.text),
            metadata_={
                "filename": "",
                "source": "document",
            },
        )
        if embeddings is not None and i < len(embeddings):
            row.embedding = embeddings[i]
        session.add(row)
        count += 1
    await session.flush()
    return count


# ---------------------------------------------------------------------------- entities


async def save_entities(session: AsyncSession, document_id: uuid.UUID,
                        entities: Sequence[Any]) -> int:
    count = 0
    for e in entities:
        session.add(
            DocumentEntity(
                document_id=document_id,
                entity_type=e.entity_type,
                value=e.value,
                confidence=e.confidence,
                occurrences=e.occurrences,
            )
        )
        count += 1
    await session.flush()
    return count


async def get_entities(session: AsyncSession, document_id: uuid.UUID) -> list[DocumentEntity]:
    stmt = select(DocumentEntity).where(DocumentEntity.document_id == document_id)
    return list((await session.execute(stmt)).scalars().all())


# ------------------------------------------------------------------------------ tables


async def save_tables(session: AsyncSession, document_id: uuid.UUID, tables: Sequence[Any]) -> int:
    count = 0
    for t in tables:
        session.add(
            DocumentTable(
                document_id=document_id,
                page_number=t.page_number,
                table_index=t.table_index,
                headers=t.headers,
                rows=t.rows,
                confidence=t.confidence,
                source=t.source,
            )
        )
        count += 1
    await session.flush()
    return count


async def get_tables(session: AsyncSession, document_id: uuid.UUID) -> list[DocumentTable]:
    stmt = select(DocumentTable).where(DocumentTable.document_id == document_id)
    return list((await session.execute(stmt)).scalars().all())


# ----------------------------------------------------------------------- extraction


async def get_extraction(session: AsyncSession, document_id: uuid.UUID, schema_type: str) -> ExtractionResult | None:
    stmt = select(ExtractionResult).where(
        ExtractionResult.document_id == document_id,
        ExtractionResult.schema_type == schema_type,
    )
    return (await session.execute(stmt)).scalars().first()


async def save_extraction(session: AsyncSession, extraction: ExtractionResult) -> None:
    session.add(extraction)
    await session.flush()


# ----------------------------------------------------------------------------- jobs


async def get_active_job(session: AsyncSession, document_id: uuid.UUID) -> ProcessingJob | None:
    stmt = select(ProcessingJob).where(
        ProcessingJob.document_id == document_id,
        ProcessingJob.status.in_(["pending", "processing", "retry"]),
    )
    return (await session.execute(stmt)).scalars().first()


async def get_job(session: AsyncSession, job_id: uuid.UUID, user_id: uuid.UUID) -> ProcessingJob | None:
    stmt = select(ProcessingJob).where(
        ProcessingJob.id == job_id, ProcessingJob.user_id == user_id
    )
    return (await session.execute(stmt)).scalars().first()


async def get_jobs_for_document(session: AsyncSession, document_id: uuid.UUID, user_id: uuid.UUID) -> list[ProcessingJob]:
    stmt = (
        select(ProcessingJob)
        .where(ProcessingJob.document_id == document_id, ProcessingJob.user_id == user_id)
        .order_by(ProcessingJob.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


# ----------------------------------------------------------------------------- audit


async def write_audit(
    session: AsyncSession,
    user_id: uuid.UUID,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail or {},
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc),
        )
    )
    await session.flush()


# ------------------------------------------------------------------------- messages


async def get_conversation(session: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation | None:
    stmt = select(Conversation).where(
        Conversation.id == conversation_id, Conversation.user_id == user_id
    )
    return (await session.execute(stmt)).scalars().first()


async def list_conversations(session: AsyncSession, user_id: uuid.UUID) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_message_history(session: AsyncSession, conversation_id: uuid.UUID, limit: int = 20) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return list(reversed(rows))
