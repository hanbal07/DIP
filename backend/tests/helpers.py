"""Helpers to generate sample documents for tests and evaluation."""
from __future__ import annotations

import io


def make_digital_pdf(text: str = "INVOICE\nInvoice Number: INV-1001\nTotal: 100.00\n") -> bytes:
    """Create a digital (text-based) PDF using PyMuPDF."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def make_scanned_pdf() -> bytes:
    """Create a scanned-looking PDF (image-only page, no text layer)."""
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    # Insert nothing as text; draw a filled rectangle to mimic a scan (no text layer).
    page.draw_rect(fitz.Rect(50, 50, 550, 750), color=(1, 1, 1), fill=(1, 1, 1))
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def make_image_bytes() -> bytes:
    from PIL import Image

    img = Image.new("RGB", (400, 300), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_txt(text: str = "Simple text document content here.") -> bytes:
    return text.encode("utf-8")


def make_malformed_pdf() -> bytes:
    # Valid magic but truncated/garbage body.
    return b"%PDF-1.4\n% this is not a valid pdf structure\n%%EOF"
