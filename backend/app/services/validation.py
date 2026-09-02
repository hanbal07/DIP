"""Upload validation: MIME type, extension, size and page limits, malformed-file checks."""
from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass

from app.core.config import settings
from app.services.storage import safe_extension

#: Maps extension -> plausible MIME (for display & authorisation).
KNOWN_MIME: dict[str, str] = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "bmp": "image/bmp",
    "gif": "image/gif",
    "webp": "image/webp",
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    "doc": "application/msword",
    "txt": "text/plain",
    "md": "text/markdown",
    "rtf": "application/rtf",
}

TEXT_EXTENSIONS = {"txt", "md", "rtf"}
IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "tiff", "tif", "bmp", "gif", "webp"}
DOC_EXTENSIONS = {"pdf", "docx", "doc"}


@dataclass
class ValidationResult:
    ok: bool
    extension: str | None
    content_type: str
    error: str | None = None
    is_image: bool = False
    is_text: bool = False
    is_pdf: bool = False
    is_word: bool = False


class ValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def validate_upload(filename: str, content_type: str | None, size_bytes: int) -> ValidationResult:
    """Validate an upload before processing. Raises ValidationError on rejection."""
    ext = safe_extension(filename or "")
    if not ext:
        raise ValidationError(
            "Unsupported or disallowed file type. Allowed: "
            + ", ".join(sorted(settings.allowed_extensions_set))
        )

    if ext not in settings.allowed_extensions_set:
        raise ValidationError(
            f"File type '.{ext}' is not allowed. Allowed: "
            + ", ".join(sorted(settings.allowed_extensions_set))
        )

    if size_bytes > settings.max_upload_size_bytes:
        raise ValidationError(
            f"File is too large. Maximum allowed size is "
            f"{settings.max_upload_size_bytes // (1024*1024)} MB."
        )

    # Validate MIME where provided; be permissive for mismatches but reject clearly
    # dangerous or obviously mismatched types.
    ctype = (content_type or "").lower()
    known = KNOWN_MIME.get(ext, "")
    if ctype and known and not is_compatible(ext, ctype):
        # txt/markdown uploads often come as octet-stream; allow those.
        if not (ext in TEXT_EXTENSIONS and ctype in ("application/octet-stream", "")):
            raise ValidationError(
                f"File content type '{ctype}' does not match extension '.{ext}'."
            )

    return ValidationResult(
        ok=True,
        extension=ext,
        content_type=ctype or known or "application/octet-stream",
        is_image=ext in IMAGE_EXTENSIONS,
        is_text=ext in TEXT_EXTENSIONS,
        is_pdf=ext == "pdf",
        is_word=ext in {"docx", "doc"},
    )


def is_compatible(ext: str, ctype: str) -> bool:
    known = KNOWN_MIME.get(ext)
    if not known:
        return True
    return ctype == known or ctype in {
        "application/octet-stream",
        "application/pdf",
    } if ext == "pdf" else ctype == known


def verify_pdf_can_open(data: bytes) -> bool:
    """Cheap sanity check that a PDF has a valid header (magic bytes only).

    Full parseability is checked by ``verify_page_count`` which opens the document with
    PyMuPDF and raises on corruption.
    """
    return bool(data and data.startswith(b"%PDF"))


def verify_page_count(data: bytes, ext: str) -> int:
    """Return page count, raising if it exceeds the configured limit."""
    if ext == "pdf":
        import fitz

        try:
            doc = fitz.open(stream=data, filetype="pdf")
            n = doc.page_count
            doc.close()
        except Exception as exc:
            raise ValidationError("PDF file is corrupted or unreadable.") from exc
        if n > settings.max_pages:
            raise ValidationError(
                f"Document has {n} pages; maximum allowed is {settings.max_pages}."
            )
        return n
    return 1
