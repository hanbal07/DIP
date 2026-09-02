"""Authentication and authorization FastAPI dependencies."""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.base import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    subject = decode_access_token(token)
    if subject is None:
        raise credentials_exc
    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise credentials_exc from exc
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc
    return user


def require_document_owner(document_user_id: uuid.UUID, current_user: User) -> None:
    """Verify that a document belongs to the current user, else 404 (avoid leaking existence)."""
    if document_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
