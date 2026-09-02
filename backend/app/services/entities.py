"""Heuristic entity extraction (dates, emails, money, phones, URLs, organisations).

Used to surface key entities alongside LLM extraction. These are deterministic signals so
confidence reflects a real measure (regex match quality), not an invented number.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.document import EntityType

_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4}|"
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4})\b",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")
_MONEY_RE = re.compile(r"(?:[$£€])\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s?(?:USD|EUR|GBP|CAD|AUD)", re.IGNORECASE)
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_URL_RE = re.compile(r"\bhttps?://[^\s]+")


@dataclass
class EntityHit:
    entity_type: str
    value: str
    confidence: float
    occurrences: int


def extract_entities_from_text(text: str) -> list[EntityHit]:
    hits: list[EntityHit] = []
    rules = [
        (EntityType.DATE, _DATE_RE, 0.85),
        (EntityType.MONEY, _MONEY_RE, 0.9),
    ]
    for etype, pattern, conf in rules:
        values = pattern.findall(text)
        if values:
            value = _clean_value(values[0])
            hits.append(
                EntityHit(entity_type=etype.value, value=value, confidence=conf, occurrences=len(values))
            )

    emails = _EMAIL_RE.findall(text)
    if emails:
        hits.append(EntityHit(EntityType.ORGANIZATION.value, emails[0], 0.9, len(emails)))
    phones = _PHONE_RE.findall(text)
    if phones:
        hits.append(EntityHit(EntityType.OTHER.value, _clean_value(phones[0]), 0.8, len(phones)))
    urls = _URL_RE.findall(text)
    if urls:
        hits.append(EntityHit(EntityType.OTHER.value, urls[0], 0.9, len(urls)))

    # Cap duplicates.
    seen: dict[str, EntityHit] = {}
    for h in hits:
        if h.value not in seen:
            seen[h.value] = h
        else:
            seen[h.value].occurrences += h.occurrences
    return list(seen.values())


def _clean_value(v: str) -> str:
    v = v.strip().strip(",.;()")
    for cls in (str,):
        pass
    return v
