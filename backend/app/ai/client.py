"""Provider factory + per-call helpers."""
from __future__ import annotations

from functools import lru_cache

from app.ai.provider import (
    AIProviderError,
    AnthropicProvider,
    BaseAIProvider,
    MockAIProvider,
    OpenAIProvider,
)
from app.core.config import settings


@lru_cache
def get_provider() -> BaseAIProvider:
    """Instantiate the configured provider. Falls back to mock if provider unset."""
    provider_name = settings.ai_provider.lower()
    if provider_name == "mock":
        return MockAIProvider()
    try:
        return _build(provider_name)
    except AIProviderError as exc:
        # In production we surface the misconfiguration, but for development the mock
        # keeps the platform usable. MOCK is never silently used in production.
        if settings.environment == "production":
            raise
        from app.core.logging import get_logger

        get_logger(__name__).warning(
            "AI provider %r unavailable (%s); falling back to mock provider",
            provider_name,
            exc,
        )
        return MockAIProvider()


def _build(name: str) -> BaseAIProvider:
    if name == "openai":
        return OpenAIProvider()
    if name == "anthropic":
        return AnthropicProvider()
    raise AIProviderError(f"unknown provider: {name}")


def ai_mode() -> str:
    return settings.ai_provider


__all__ = ["get_provider", "ai_mode", "AIProviderError"]
