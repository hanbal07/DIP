"""Security helpers: password hashing and JWT tokens."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_ALGORITHM = settings.algorithm


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Return the token subject (user id) or None if invalid/expired."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[_ALGORITHM]
        )
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
