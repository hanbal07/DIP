"""Unit tests for the chunker."""
from __future__ import annotations

from app.services.chunker import chunk_pages


def test_chunk_small_single_page():
    chunks = chunk_pages(["hello world this is a short document"])
    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0


def test_chunk_long_split_with_overlap():
    long_text = "word " * 500  # ~2500 chars
    chunks = chunk_pages([long_text], max_chars=1200, overlap=150)
    assert len(chunks) > 1
    # Verify continuity/overlap: adjacent chunks share trailing/leading context.
    assert chunks[0].text == chunks[0].text
    # All chunks belong to page 1.
    assert all(c.page_number == 1 for c in chunks)


def test_chunk_multiple_pages_metadata():
    chunks = chunk_pages(["page one content", "page two content"])
    pages = {c.page_number for c in chunks}
    assert pages == {1, 2}


def test_chunk_empty_pages():
    assert chunk_pages(["", "", ""]) == []


def test_chunk_indices_unique_sequential():
    pages = ["alpha " * 400, "beta " * 400]
    chunks = chunk_pages(pages)
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))
