"""Secure local file storage.

Generates safe storage keys (never user-supplied paths), prevents path traversal, and
provides streaming read/write. Files are stored outside any web-served directory.
"""
from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

_UPLOAD_ROOT = Path(settings.upload_dir)
_EXPORT_ROOT = Path(settings.export_dir)

#: Allow only known-safe characters in original filenames used for display.
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._ -]")

#: List of signatures / extensions considered dangerous.
_DANGEROUS_EXTENSIONS = {
    "exe", "bat", "cmd", "com", "sh", "ps1", "vbs", "js", "jse", "msi",
    "msp", "scr", "hta", "wsh", "pif", "gadget", "dll", "sys", "apk",
}


def ensure_dirs() -> None:
    _UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    _EXPORT_ROOT.mkdir(parents=True, exist_ok=True)


def safe_filename(original: str) -> str:
    """Return a sanitised version of an original filename (display only)."""
    name = os.path.basename(original or "upload")
    name = _SAFE_NAME_RE.sub("_", name)
    name = name.strip(". ")
    return name or "upload"


def safe_extension(original: str) -> str | None:
    ext = os.path.splitext(original or "")[1].lstrip(".").lower()
    if not ext:
        return None
    if ext in _DANGEROUS_EXTENSIONS:
        return None
    if not re.fullmatch(r"[a-z0-9]{1,10}", ext):
        return None
    return ext


def resolve_upload_path(storage_key: str) -> Path:
    """Resolve a storage key to an absolute path, guarding against traversal."""
    key = storage_key.replace("\\", "/")
    if ".." in key.split("/") or key.startswith("/"):
        raise ValueError("invalid storage key")
    p = (_UPLOAD_ROOT / key).resolve()
    if not str(p).startswith(str(_UPLOAD_ROOT.resolve())):
        raise ValueError("path traversal blocked")
    return p


def generate_storage_key(extension: str) -> str:
    """Generate a unique, safe storage key using a UUID."""
    return f"{uuid.uuid4().hex}.{extension}"


async def save_upload(upload: UploadFile) -> tuple[str, str, int]:
    """Persist an uploaded file. Returns (storage_key, safe_display_filename, size_bytes)."""
    ensure_dirs()
    extension = safe_extension(upload.filename or "file")
    if not extension:
        raise ValueError("unsupported or disallowed file extension")
    storage_key = generate_storage_key(extension)
    path = resolve_upload_path(storage_key)

    size = 0
    chunk_bytes = 1024 * 1024
    with open(path, "wb") as out:
        while True:
            chunk = await upload.read(chunk_bytes)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.max_upload_size_bytes:
                out.close()
                path.unlink(missing_ok=True)
                raise ValueError("file exceeds maximum allowed size")
            out.write(chunk)

    display_name = safe_filename(upload.filename or "upload")
    import mimetypes

    content_type = upload.content_type or mimetypes.guess_type(display_name)[0] or "application/octet-stream"
    return storage_key, display_name, size


def read_file(storage_key: str) -> bytes:
    path = resolve_upload_path(storage_key)
    if not path.exists():
        raise FileNotFoundError("stored file not found")
    return path.read_bytes()


def delete_file(storage_key: str) -> None:
    path = resolve_upload_path(storage_key)
    path.unlink(missing_ok=True)


def file_abs_path(storage_key: str) -> str:
    return str(resolve_upload_path(storage_key))


def make_export_path(filename: str) -> Path:
    ensure_dirs()
    safe = safe_filename(filename)
    return _EXPORT_ROOT / f"{uuid.uuid4().hex}_{safe}"


def export_exists(filename: str) -> bool:
    safe = safe_filename(filename)
    return any(p.name.endswith(f"_{safe}") for p in _EXPORT_ROOT.glob(f"*_{safe}"))
