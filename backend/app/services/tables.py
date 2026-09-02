"""Table detection and extraction.

Uses pdfplumber for digitally-embedded PDF tables and a heuristic for text-rendered tables.
Preserves headers, rows, values, page number and a source flag + confidence (real signal:
how structured/delimited the detected table is).
"""
from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass

from app.services.text_extraction import normalize_text

logger = logging.getLogger(__name__)


@dataclass
class DetectedTable:
    page_number: int
    table_index: int
    headers: list[str]
    rows: list[list[str]]
    confidence: float
    source: str  # "pdf" | "llm" | "heuristic"


def extract_tables_pdf(pdf_bytes: bytes) -> list[DetectedTable]:
    """Extract tables from a digital PDF using pdfplumber."""
    tables: list[DetectedTable] = []
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                extracted = page.extract_tables()
                for tidx, raw in enumerate(extracted):
                    if not raw:
                        continue
                    cleaned = _clean_pdfplumber(raw)
                    if not cleaned:
                        continue
                    headers = cleaned[0] if cleaned else []
                    rows = cleaned[1:] if len(cleaned) > 1 else []
                    confidence = _table_confidence(headers, rows)
                    tables.append(
                        DetectedTable(
                            page_number=page_index,
                            table_index=tidx,
                            headers=headers,
                            rows=rows,
                            confidence=confidence,
                            source="pdf",
                        )
                    )
    except Exception as exc:  # pragma: no cover
        logger.warning("pdfplumber table extraction failed: %s", exc)
    return tables


def _clean_pdfplumber(raw: list[list]) -> list[list[str]]:
    out: list[list[str]] = []
    for row in raw:
        cells: list[str] = []
        for cell in row:
            if cell is None:
                cells.append("")
            else:
                cells.append(normalize_text(str(cell)))
        if any(cells):
            out.append(cells)
    return out


def _table_confidence(headers: list[str], rows: list[list[str]]) -> float:
    """Confidence from real structure: complete rows, header presence, cell fill ratio."""
    if not rows:
        return 0.3
    total_cells = sum(len(r) for r in rows)
    filled = sum(1 for r in rows for c in r if c and c.strip())
    fill_ratio = (filled / total_cells) if total_cells else 0.0
    ncols = max([len(r) for r in ([headers] + rows) if r] or [0])
    has_header = any(h and h.strip() for h in headers)
    conf = 0.4 + 0.3 * fill_ratio + (0.2 if has_header else 0.0)
    if ncols >= 2:
        conf += 0.1
    return round(min(conf, 0.98), 3)


def detect_text_tables(page_text: str) -> list[list[str]]:
    """Heuristic: detect pipe/delimited tables in free text."""
    out: list[list[str]] = []
    for block in re.split(r"\n\s*\n", page_text):
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue
        if all("|" in l or "\t" in l for l in lines[:2]):
            rows = [re.split(r"\s*\|\s*|\t+", l) for l in lines]
            out.append([r for r in rows if any(cell for cell in r)])
    return out
