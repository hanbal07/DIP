"""Tests for the deterministic mock AI provider."""
from __future__ import annotations

import pytest

from app.ai.provider import MockAIProvider


@pytest.mark.asyncio
async def test_mock_structured_conforms_to_example():
    provider = MockAIProvider()
    example = {"document_type": "invoice"}
    result = await provider.chat_structured(
        system="s", user="text", schema_name="x", example=example
    )
    assert isinstance(result, dict)
    assert "document_type" in result


@pytest.mark.asyncio
async def test_mock_embeddings_deterministic():
    provider = MockAIProvider()
    a1 = await provider.embed_texts(["hello world"])
    a2 = await provider.embed_texts(["hello world"])
    assert a1 == a2
    assert len(a1[0]) > 0


@pytest.mark.asyncio
async def test_mock_embeddings_similar_docs_closer():
    provider = MockAIProvider()
    e1 = (await provider.embed_texts(["the cat sat on the mat"]))[0]
    e2 = (await provider.embed_texts(["the cat sat on the mat"]))[0]
    e3 = (await provider.embed_texts(["quantum physics and rockets"]))[0]
    import math

    def cos(a, b):
        return sum(x * y for x, y in zip(a, b))

    assert cos(e1, e2) > cos(e1, e3)


@pytest.mark.asyncio
async def test_mock_freeform():
    provider = MockAIProvider()
    out = await provider.chat_freeform(system="s", user="hi")
    assert isinstance(out, str)
