"""Unit tests for upload validation logic."""
from __future__ import annotations

import pytest

from app.services.validation import (
    ValidationError,
    validate_upload,
    verify_pdf_can_open,
)


def test_accepts_pdf():
    r = validate_upload("invoice.pdf", "application/pdf", 1000)
    assert r.ok
    assert r.extension == "pdf"
    assert r.is_pdf


def test_accepts_image():
    r = validate_upload("scan.png", "image/png", 1000)
    assert r.ok
    assert r.is_image


def test_rejects_dangerous_extension():
    with pytest.raises(ValidationError):
        validate_upload("evil.exe", "application/octet-stream", 1000)


def test_rejects_disallowed_extension():
    with pytest.raises(ValidationError):
        validate_upload("file.xyz", "application/xyz", 1000)


def test_rejects_oversized_file(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_upload_size_bytes", 100)
    with pytest.raises(ValidationError):
        validate_upload("big.pdf", "application/pdf", 1000)


def test_mime_mismatch_rejected():
    with pytest.raises(ValidationError):
        validate_upload("doc.pdf", "text/html", 1000)


def test_text_with_octet_stream_allowed():
    r = validate_upload("notes.txt", "application/octet-stream", 1000)
    assert r.ok


def test_pdf_magic_number():
    assert verify_pdf_can_open(b"%PDF-1.4\n%----\n")
    assert not verify_pdf_can_open(b"not a pdf")
