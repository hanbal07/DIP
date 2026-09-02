"""RAG chat endpoints with conversations, multi-document support, and citations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.document import (
    ChatRequest,
    ChatResponse,
    CitationOut,
    ConversationOut,
    MessageOut,
)
from app.services import repositories
from app.services.qa import answer_with_rag
from app.services.retrieval import embed_query, semantic_search

router = APIRouter(prefix="/chat", tags=["chat"])


async def _resolve_document_ids(
    db: AsyncSession,
    user_id: uuid.UUID,
    requested: list[uuid.UUID] | None,
) -> list[uuid.UUID]:
    """Resolve requested document ids, verifying ownership of each.

    If `requested` is None, we leave scope as "all user documents" (None) — but the caller
    decides. Here we return the validated list or None for global scope.
    """
    if requested is None:
        return []
    owned: list[uuid.UUID] = []
    for doc_id in requested:
        doc = await repositories.get_owned_document(db, user_id, doc_id)
        if doc is not None:
            owned.append(doc_id)
    # Ignore ids the user doesn't own; do not leak which were rejected.
    return owned


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await repositories.list_conversations(db, current_user.id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    convo = await repositories.get_conversation(db, conversation_id, current_user.id)
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await repositories.get_message_history(db, conversation_id)
    # Filter out empty/placeholder messages.
    return [m for m in messages]


@router.delete("/conversations/{conversation_id}", status_code=200)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    convo = await repositories.get_conversation(db, conversation_id, current_user.id)
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    # Delete messages + citations via cascade.
    await db.execute(Message.__table__.delete().where(Message.conversation_id == convo.id))
    await db.delete(convo)
    await db.commit()
    await repositories.write_audit(
        db, current_user.id, "conversation.delete", "conversation", str(conversation_id)
    )
    return {"message": "Conversation deleted"}


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    # Resolve conversation (validate ownership).
    conversation: Conversation | None = None
    if payload.conversation_id:
        conversation = await repositories.get_conversation(
            db, payload.conversation_id, current_user.id
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        # Ensure the conversation's document is still owned (if scoped to one doc).
        if conversation.document_id is not None:
            doc = await repositories.get_owned_document(db, current_user.id, conversation.document_id)
            if doc is None:
                raise HTTPException(status_code=403, detail="Document access revoked")

    # Resolve document scope with ownership check.
    scope_ids = await _resolve_document_ids(db, current_user.id, payload.document_ids)

    # Retrieve context.
    query_embedding = await embed_query(payload.question)
    chunks = await semantic_search(
        db,
        user_id=current_user.id,
        query_embedding=query_embedding,
        document_ids=(scope_ids if scope_ids else payload.document_ids if payload.document_ids else None),
        limit=8,
    )

    # Build conversation history (previous messages) for multi-turn context.
    history: list[dict] = []
    if conversation:
        prev = await repositories.get_message_history(db, conversation.id, limit=10)
        history = [{"role": m.role, "content": m.content} for m in prev]

    answer, citations, has_evidence = await answer_with_rag(
        payload.question, chunks, conversation_history=history
    )

    # Persist conversation + messages + citations.
    if conversation is None:
        conversation = Conversation(
            user_id=current_user.id,
            document_id=(scope_ids[0] if len(scope_ids) == 1 else None),
            title=payload.question[:100],
        )
        db.add(conversation)
        await db.flush()

    db.add(Message(conversation_id=conversation.id, role="user", content=payload.question))
    assistant = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        citations=[c.to_dict() for c in citations],
    )
    db.add(assistant)
    await db.flush()

    # Persist citations for auditability.
    for c in citations:
        from app.models.conversation import Citation

        db.add(
            Citation(
                message_id=assistant.id,
                document_id=c.document_id,
                user_id=current_user.id,
                page_number=c.page_number,
                snippet=c.snippet[:800],
                chunk_id=None,
                score=c.score,
                document_filename=c.document_filename,
            )
        )

    await db.commit()
    await db.refresh(conversation)

    citation_out = [
        CitationOut(
            document_id=c.document_id,
            document_filename=c.document_filename,
            page_number=c.page_number,
            snippet=c.snippet,
            score=c.score,
        )
        for c in citations
    ]

    return ChatResponse(
        answer=answer,
        conversation_id=conversation.id,
        question=payload.question,
        citations=citation_out,
        has_sufficient_evidence=has_evidence,
        used_document_ids=list({c.document_id for c in citations}),
    )
