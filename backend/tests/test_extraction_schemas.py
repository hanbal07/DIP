"""Unit tests for extraction schema validation and document callables."""
from __future__ import annotations

from app.ai.schemas import SUPPORTED_DOCUMENT_TYPES, get_schema, schema_fields, validate_structured


def test_supported_types_present():
    for t in ["invoice", "receipt", "resume", "contract", "report", "research_paper", "form", "certificate", "unknown"]:
        assert t in SUPPORTED_DOCUMENT_TYPES


def test_get_schema_unknown_fallback():
    assert get_schema("nonexistent") == get_schema("unknown")


def test_validate_structured_fills_missing():
    schema = get_schema("invoice")
    data, warnings = validate_structured("invoice", {"invoice_number": "INV-1"})
    for key in schema:
        assert key in data
    assert data["invoice_number"] == "INV-1"


def test_validate_structured_drops_extra_keys():
    data, _ = validate_structured("invoice", {"invoice_number": "X", "totally_extra": "nope"})
    assert "totally_extra" not in data


def test_validate_structured_numeric():
    data, _ = validate_structured("invoice", {"subtotal": "100.50"})
    assert data["subtotal"] == "100.50"


def test_schema_fields():
    fields = schema_fields("invoice")
    assert "invoice_number" in fields
