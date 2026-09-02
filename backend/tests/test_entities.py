"""Unit tests for entity extraction heuristics."""
from __future__ import annotations

from app.services.entities import extract_entities_from_text


def test_extracts_email():
    hits = extract_entities_from_text("Contact alice@example.com for details")
    emails = [h.value for h in hits]
    assert "alice@example.com" in emails


def test_extracts_date():
    hits = extract_entities_from_text("Invoice dated 2024-03-15")
    assert any(h.entity_type == "DATE" for h in hits)


def test_extracts_money():
    hits = extract_entities_from_text("Total due: $1,250.00")
    assert any(h.entity_type == "MONEY" for h in hits)


def test_empty_text():
    assert extract_entities_from_text("") == []
