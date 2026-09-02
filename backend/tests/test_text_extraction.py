"""Unit tests for text extraction and normalization."""
from __future__ import annotations

from app.services.text_extraction import normalize_text, extract_pdf_digital, extract_plain


def test_normalize_removes_control_chars():
    text = "hello\x00\x1fworld  \n\n\n\nnewpara"
    out = normalize_text(text)
    assert "\x00" not in out
    assert "\x1f" not in out
    assert "\n\n\n\n" not in out


def test_normalize_strips():
    assert normalize_text("  hi  ") == "hi"


def test_extract_plain():
    result = extract_plain("  one\n\ntwo  ")
    assert result.method == "digital"
    assert result.pages[0].text == "one\n\ntwo"
    assert result.confidence == 1.0


def test_extract_plain_empty():
    result = extract_plain("   ")
    assert result.pages == []
    assert result.method == "none"
