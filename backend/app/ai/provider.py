"""AI service provider abstraction.

Supports a configurable provider (OpenAI, Anthropic) plus a deterministic ``mock`` mode
used for tests and development so the platform never depends on live LLM/embedding APIs
to run its test suite.

Document text is treated as untrusted data injected into prompts as *content* under strict
system instructions. We deliberately do not translate document instructions into system
behavior.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- errors


class AIProviderError(Exception):
    """Base error for provider failures."""


class AITimeoutError(AIProviderError):
    pass


class AIRateLimitError(AIProviderError):
    pass


class AIUnavailableError(AIProviderError):
    pass


class AISchemaError(AIProviderError):
    """Model output failed schema validation."""


# ---------------------------------------------------------------------- (de)serialise

def ensure_list_2d(value: Any) -> list[list[str]]:
    """Best-effort coercion of LLM table output into a 2D list of strings."""
    if not isinstance(value, list):
        return []
    out: list[list[str]] = []
    for row in value:
        if isinstance(row, dict):
            keys = list(row.keys())
            out.append([str(row[k]) if row.get(k) is not None else "" for k in keys])
        elif isinstance(row, (list, tuple)):
            out.append([str(c) for c in row])
        elif row is not None:
            out.append([str(row)])
    return out


# --------------------------------------------------------------------------- base provider


class BaseAIProvider(ABC):
    """Common interface implemented by concrete providers and the mock."""

    name: str = "base"

    @abstractmethod
    async def chat_structured(
        self,
        *,
        system: str,
        user: str,
        schema_name: str,
        example: dict[str, Any],
    ) -> dict[str, Any]:
        """Return model output conforming to the given `example` (schema) shape."""

    @abstractmethod
    async def chat_freeform(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1000,
    ) -> str:
        """Return free-form text (e.g. answers)."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return a list of embeddings, one per input text."""

    def _pure_retry(self, fn, *args, **kwargs):
        """Retry wrapper shared by providers (avoid duplicated loop logic)."""
        last_exc: Exception | None = None
        for attempt in range(settings.provider_max_retries):
            try:
                return fn(*args, **kwargs)
            except (AIRateLimitError, AITimeoutError, AIUnavailableError) as exc:
                last_exc = exc
                wait = 1.0 * (2 ** attempt)
                logger.warning(
                    "Provider transient failure (%s), retry %d/%d after %.1fs",
                    type(exc).__name__,
                    attempt + 1,
                    settings.provider_max_retries,
                    wait,
                )
                time.sleep(wait)
        if last_exc is not None:
            raise last_exc
        raise AIProviderError("retry loop exhausted")


class OpenAIProvider(BaseAIProvider):
    name = "openai"

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise AIProviderError("OPENAI_API_KEY is not configured")
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url or "https://api.openai.com/v1"
        self.chat_model = settings.openai_chat_model
        self.embedding_model = settings.openai_embedding_model

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=settings.provider_timeout_seconds,
        )

    async def chat_structured(self, *, system, user, schema_name, example):
        async def _call():
            payload = {
                "model": self.chat_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {
                    "type": "json_object",
                    "schema": example,
                },
                "temperature": 0,
            }
            async with self._client() as client:
                resp = await client.post("/chat/completions", json=payload)
                self._raise_for_status(resp)
                data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)

        return await self._pure_retry(_call)

    async def chat_freeform(self, *, system, user, max_tokens=1000):
        async def _call():
            payload = {
                "model": self.chat_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.2,
            }
            async with self._client() as client:
                resp = await client.post("/chat/completions", json=payload)
                self._raise_for_status(resp)
                data = resp.json()
            return data["choices"][0]["message"]["content"]

        return await self._pure_retry(_call)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        async def _call():
            payload = {
                "model": self.embedding_model,
                "input": texts,
            }
            async with self._client() as client:
                resp = await client.post("/embeddings", json=payload)
                self._raise_for_status(resp)
                data = resp.json()
            ordered = sorted(data["data"], key=lambda d: d["index"])
            return [d["embedding"] for d in ordered]

        return await self._pure_retry(_call)

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code == 429:
            raise AIRateLimitError(resp.text[:300])
        if resp.status_code >= 500:
            raise AIUnavailableError(resp.text[:300])
        resp.raise_for_status()


class AnthropicProvider(BaseAIProvider):
    name = "anthropic"

    def __init__(self) -> None:
        if not settings.anthropic_api_key:
            raise AIProviderError("ANTHROPIC_API_KEY is not configured")
        self.api_key = settings.anthropic_api_key
        self.model = settings.anthropic_model

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            headers=self._headers(),
            timeout=settings.provider_timeout_seconds,
        )

    async def chat_structured(self, *, system, user, schema_name, example):
        async def _call():
            async with self._client() as client:
                resp = await client.post(
                    "/v1/messages",
                    json={
                        "model": self.model,
                        "max_tokens": 2000,
                        "system": system,
                        "messages": [{"role": "user", "content": user}],
                        "temperature": 0,
                    },
                )
                self._raise_for_status(resp)
                data = resp.json()
            content = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            # Extract JSON object from response text.
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1:
                raise AISchemaError("no JSON object in response")
            return json.loads(content[start : end + 1])

        return await self._pure_retry(_call)

    async def chat_freeform(self, *, system, user, max_tokens=1000):
        async def _call():
            async with self._client() as client:
                resp = await client.post(
                    "/v1/messages",
                    json={
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "system": system,
                        "messages": [{"role": "user", "content": user}],
                        "temperature": 0.2,
                    },
                )
                self._raise_for_status(resp)
                data = resp.json()
            return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

        return await self._pure_retry(_call)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise AISchemaError("Anthropic provider has no embedding endpoint; use OPENAI_API_KEY for embeddings")

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code == 429:
            raise AIRateLimitError(resp.text[:300])
        if resp.status_code >= 500:
            raise AIUnavailableError(resp.text[:300])
        resp.raise_for_status()


# --------------------------------------------------------------------------- mock provider


class MockAIProvider(BaseAIProvider):
    """Deterministic AI provider for tests/dev.

    Produces schema-compatible, stable output based on prompt content so tests are
    repeatable and do not depend on any external service. NEVER used to fake production
    results — it is only active when ``AI_PROVIDER=mock``.
    """

    name = "mock"

    async def chat_freeform(self, *, system, user, max_tokens=1000):
        # Deterministic echo/truncate for tests; not a real model.
        return user[: max_tokens or 1000] if isinstance(user, str) else str(user)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embedding_from_text(t) for t in texts]

    def _embedding_from_text(self, text: str) -> list[float]:
        """Deterministic bag-of-words style hash embedding."""
        dim = settings.embedding_dimensions
        vec = [0.0] * dim
        tokens = re.findall(r"\w+", text.lower())
        for tok in tokens:
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx] += sign
        # Normalise.
        norm = (sum(v * v for v in vec) ** 0.5) or 1.0
        return [v / norm for v in vec]

    async def chat_structured(self, *, system, user, schema_name, example):
        return self._structured_from_example(user, example)

    def _structured_from_example(self, user: str, example: dict[str, Any]) -> dict[str, Any]:
        def fill(value: Any) -> Any:
            if isinstance(value, dict):
                return {k: fill(v) for k, v in value.items()}
            if isinstance(value, list):
                if value:
                    return [fill(value[0])]
                return []
            if isinstance(value, bool):
                # bool is subclass of int; check first.
                return bool(re.search(r"\btrue\b|\byes\b", user, re.I)) and False
            if isinstance(value, str):
                if value.strip().startswith("__"):
                    return self._mock_scalar(value[2:], user)
                return str(value)
            if isinstance(value, (int, float)):
                return float(len(re.findall(r"\w+", user, re.I)) % 100) + 1
            return value

        out = {}
        for k, v in example.items():
            out[k] = fill(v)
        return out

    @staticmethod
    def _mock_scalar(field: str, user: str) -> str:
        """Return a plausible-but-deterministic value for a field placeholder."""
        lower = user.lower()
        f = field.lower()
        if "date" in f:
            return "2024-01-15"
        if "email" in f:
            return "contact@example.com"
        if "amount" in f or "total" in f or "price" in f:
            m = re.search(r"[$£€]\s?([\d,]+\.?\d*)", user)
            return m.group(1) if m else "100.00"
        if "number" in f or "invoice" in f or "id" in f:
            return "INV-1001"
        if "name" in f:
            return "ACME Corporation"
        if "currency" in f:
            return "USD"
        if "confidence" in f:
            return "high"
        if "table" in f:
            return "[]"
        if "founded" in f or "year" in f:
            return "1999"
        return "example"
