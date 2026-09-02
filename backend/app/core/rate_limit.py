"""Simple fixed-window in-memory rate limiter for expensive endpoints.

Production systems would use Redis; for this platform a bounded in-memory limiter (per
worker) provides reasonable abuse protection for chat/embedding endpoints without adding a
hard infra dependency. Documented limitation: not shared across multiple worker processes.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RateLimiter:
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._window = 60.0
        self._last_cleanup = time.monotonic()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        # Periodic cleanup to bound memory.
        if now - self._last_cleanup > 120:
            for k in list(self._hits.keys()):
                q = self._hits[k]
                while q and now - q[0] > self._window:
                    q.popleft()
                if not q:
                    del self._hits[k]
            self._last_cleanup = now

        q = self._hits[key]
        while q and now - q[0] > self._window:
            q.popleft()
        if len(q) >= self.requests_per_minute:
            return False
        q.append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies per-user rate limiting to 'expensive' AI routes (chat, search)."""

    EXPENSIVE_PREFIXES = ("/chat", "/search")

    def __init__(
        self,
        app,
        chat_per_minute: int = 15,
        general_per_minute: int = 60,
    ):
        super().__init__(app)
        self.limiters = {
            "chat": RateLimiter(chat_per_minute),
            "general": RateLimiter(general_per_minute),
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in self.EXPENSIVE_PREFIXES):
            user_key = request.headers.get("x-forwarded-for", request.client.host if request.client else "anon")
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                # Use a hashed subject of the token for rate keying; do not log tokens.
                import hashlib

                user_key = hashlib.sha256(auth.encode()).hexdigest()[:16]
            limiter = self.limiters["chat"] if path.startswith("/chat") else self.limiters["general"]
            if not limiter.allow(user_key):
                return Response(
                    content='{"detail":"Rate limit exceeded. Please slow down."}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json",
                    headers={"Retry-After": "60"},
                )
        return await call_next(request)
