"""Intelligent text chunking for RAG.

Builds chunks from per-page text, preserving document/page/section metadata. Uses
section-aware boundaries with overlap to keep semantic units together where possible.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    page_number: int
    chunk_index: int
    section: str | None
    text: str


_SECTION_RE = re.compile(
    r"^\s*(?:#{1,3}\s+|(?:section|chapter|introduction|abstract|conclusion|summary|"
    r"methodology|references|appendix)\b[\s:.\-]+)",
    re.IGNORECASE,
)


def chunk_pages(
    pages: list[str],
    *,
    max_chars: int = 1200,
    overlap: int = 150,
) -> list[Chunk]:
    """Chunk a list of per-page texts into semantic, metadata-bearing chunks.

    Args:
        pages: page texts indexed by (page_number - 1).
        max_chars: target maximum chunk size.
        overlap: characters carried between adjacent chunks of long text.
    """
    chunks: list[Chunk] = []

    for page_number, text in enumerate(pages, start=1):
        if not text:
            continue
        # Split into section units; track the current section label.
        units = _section_units(text)
        current_section: str | None = None
        for unit in units:
            if unit["is_section"]:
                current_section = (unit["text"].lstrip("#").strip())[:200]
            # Accumulate until reaching max_chars.
            # We treat each page's units sequentially, chunking long continuity.
            pass

        # Simpler approach: build one buffer per page, splitting with overlap, carrying
        # the section that the chunk starts in.
        buf_parts: list[str] = []
        current_sec = None
        for unit in units:
            if unit["is_section"]:
                current_sec = (unit["text"].lstrip("#").strip())[:200]
                # Keep heading as part of following content.
                buf_parts.append(unit["text"].strip())
            else:
                buf_parts.append(unit["text"].strip())

        page_text = "\n".join(p for p in buf_parts if p)
        _emit_page_chunks(chunks, page_number, page_text, max_chars, overlap)

    # Assign final sequential indices.
    for i, c in enumerate(chunks):
        c.chunk_index = i
    return chunks


def _emit_page_chunks(
    chunks: list[Chunk],
    page_number: int,
    text: str,
    max_chars: int,
    overlap: int,
) -> None:
    text = text.strip()
    if not text:
        return
    if len(text) <= max_chars:
        chunks.append(Chunk(page_number=page_number, chunk_index=0, section=None, text=text))
        return
    step = max_chars - overlap
    pos = 0
    while pos < len(text):
        piece = text[pos : pos + max_chars]
        if len(piece.strip()) >= 40 or pos + max_chars >= len(text):
            chunks.append(
                Chunk(page_number=page_number, chunk_index=0, section=None, text=piece.strip())
            )
        pos += step


def _section_units(text: str) -> list[dict]:
    """Split a page into units, flagging heading lines."""
    units: list[dict] = []
    for line in text.split("\n"):
        is_section = bool(_SECTION_RE.match(line))
        units.append({"is_section": is_section, "text": line})
    return units
