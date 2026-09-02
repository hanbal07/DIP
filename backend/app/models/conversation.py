"""Conversation, message and citation/source models for document chat / RAG."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict, MutableList

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A chat conversation. Scoped to a user and (usually) a single document.

    ``document_id`` may be null for a future global multi-document chat, but the platform
    currently ties conversations to one or more authorized documents via messages' sources.
    """

    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=True)

    owner = relationship("User", back_populates="conversations")
    document = relationship("Document", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single message in a conversation, with optional citations to retrieved chunks."""

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    #: List of Citation dicts attached to assistant answers.
    citations: Mapped[list[dict]] = mapped_column(MutableList.as_mutable(JSON), default=list)
    #: evidence summary + metadata for observability (no document content leakage in logs).
    metadata_: Mapped[dict] = mapped_column(
        "metadata_json", MutableDict.as_mutable(JSON), default=dict
    )

    conversation = relationship("Conversation", back_populates="messages")


class Citation(Base):
    """Persistent record of a source used to support an answer (in addition to the inline
    citations embedded in Message.citations). Kept for auditability.

    This is intentionally a light snapshot table (denormalised) so citations survive even
    if chunks are later deleted.
    """

    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Short excerpt of the supporting text (trimmed) for display.
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    score: Mapped[float] = mapped_column(default=0.0)
    document_filename: Mapped[str] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False
    )
