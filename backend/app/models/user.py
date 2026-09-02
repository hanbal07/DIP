"""User model and password helpers."""
from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An authenticated user. All owned data is scoped by ``user_id``."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(default=False, nullable=False)

    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    conversations = relationship(
        "Conversation", back_populates="owner", cascade="all, delete-orphan"
    )
    audit_logs = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
