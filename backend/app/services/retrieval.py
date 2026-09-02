"""Semantic retrieval over pgvector embeddings.

Retrieval is strictly ownership-aware: we always filter by the requesting user's id so no
chunk belonging to another user can ever be returned. Uses cosine distance (<=>).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.ai.client import get_provider
from app.core.config import settings
from app.models.document import Document, DocumentChunk


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_filename: str
    page_number: int
    chunk_index: int
    section: str | None
    text: str
    score: float  # cosine similarity (higher = closer)


async def embed_query(query: str) -> list[float]:
    provider = get_provider()
    vector = await provider.embed_texts([query])
    return vector[0]


async def semantic_search(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    query_embedding: list[float],
    document_ids: list[uuid.UUID] | None = None,
    limit: int = 8,
) -> list[RetrievedChunk]:
    """Retrieve the most similar chunks for a user, optionally scoped to documents.

    Uses native pgvector cosine distance (<=>) on PostgreSQL. On SQLite (tests / lightweight
    dev without pgvector) it falls back to an in-process cosine computation so development
    and the test suite require no vector database.
    """
    if session.bind and str(session.bind.dialect.name) == "sqlite":
        return await _semantic_search_python(
            session, user_id=user_id, query_embedding=query_embedding,
            document_ids=document_ids, limit=limit,
        )
    return await _semantic_search_pg(
        session, user_id=user_id, query_embedding=query_embedding,
        document_ids=document_ids, limit=limit,
    )


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def _semantic_search_python(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    query_embedding: list[float],
    document_ids: list[uuid.UUID] | None = None,
    limit: int,
) -> list[RetrievedChunk]:
    """Cosine-based retrieval fallback for SQLite (tests / dev)."""
    from sqlalchemy import select, cast, String

    stmt = (
        select(DocumentChunk, Document.filename)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.user_id == user_id, DocumentChunk.embedding.isnot(None))
        .order_by(DocumentChunk.page_number, DocumentChunk.chunk_index)
    )
    # We can't use native pgvector on SQLite, so we load embeddings as text and parse.
    # To keep this dependency-light we query documents+chunks and compute cosine, but the
    # embedding column is a string on SQLite. Parse it.
    results = (await session.execute(stmt)).all()
    scored: list[tuple[float, object]] = []
    for chunk, filename in results:
        emb = getattr(chunk, "embedding", None)
        if emb is None:
            continue
        vec = _parse_embedding(emb)
        if not vec:
            continue
        score = _cosine(query_embedding, vec)
        scored.append((score, (chunk, filename)))
    scored.sort(key=lambda t: t[0], reverse=True)
    out: list[RetrievedChunk] = []
    for score, (chunk, filename) in scored[:limit]:
        if document_ids and chunk.document_id not in document_ids:
            continue
        out.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_filename=filename,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                section=chunk.section,
                text=chunk.text,
                score=float(score or 0.0),
            )
        )
    return out


def _parse_embedding(value: object) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]
        parts = s.split(",")
        try:
            return [float(p.strip()) for p in parts if p.strip()]
        except ValueError:
            return None
    if isinstance(value, (list, tuple)):
        try:
            return [float(v) for v in value]
        except (TypeError, ValueError):
            return None
    return None


async def _semantic_search_pg(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    query_embedding: list[float],
    document_ids: list[uuid.UUID] | None = None,
    limit: int = 8,
) -> list[RetrievedChunk]:
    vec_literal = "[" + ",".join(str(float(v)) for v in query_embedding) + "]"

    extra = ""
    params: dict = {"qvec": vec_literal, "user_id": str(user_id), "limit": limit}
    if document_ids:
        ids = ",".join(f"'{d}'" for d in document_ids)
        extra = f"AND c.document_id IN ({ids})"

    base = text(
        """
        SELECT
            c.id AS chunk_id,
            c.document_id,
            d.filename AS document_filename,
            c.page_number,
            c.chunk_index,
            c.section,
            c.text,
            1 - (c.embedding <=> :qvec) AS score
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.user_id = :user_id
          AND c.embedding IS NOT NULL
          {extra}
        ORDER BY c.embedding <=> :qvec
        LIMIT :limit
        """.replace("{extra}", extra)
    )

    result = await session.execute(base, params)
    rows = result.mappings().all()

    out: list[RetrievedChunk] = []
    for r in rows:
        out.append(
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                document_filename=r["document_filename"],
                page_number=r["page_number"],
                chunk_index=r["chunk_index"],
                section=r["section"],
                text=r["text"],
                score=float(r["score"] or 0.0),
            )
        )
    return out


def cosine_similarity_query(vec_literal: str) -> str:
    """Helper returning the SQL fragment for cosine similarity ordering."""
    return f"1 - (embedding <=> {vec_literal})"
