"""Semantic search over user-owned document embeddings."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.user import User
from app.schemas.document import SearchHit, SearchResponse
from app.services import repositories
from app.services.retrieval import embed_query, semantic_search

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=300),
    document_id: uuid.UUID | None = Query(None),
    limit: int = Query(8, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    # Validate document ownership if a specific doc is requested.
    scoped_ids: list[uuid.UUID] | None = None
    if document_id is not None:
        doc = await repositories.get_owned_document(db, current_user.id, document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        scoped_ids = [document_id]

    query_embedding = await embed_query(q)
    chunks = await semantic_search(
        db, user_id=current_user.id, query_embedding=query_embedding,
        document_ids=scoped_ids, limit=limit,
    )

    hits = []
    for c in chunks:
        snippet = c.text[:400]
        hits.append(
            SearchHit(
                document_id=c.document_id,
                document_filename=c.document_filename,
                page_number=c.page_number,
                chunk_index=c.chunk_index,
                section=c.section,
                text=c.text,
                score=round(c.score, 4),
                snippet=snippet,
            )
        )
    return SearchResponse(query=q, hits=hits, total=len(hits))
