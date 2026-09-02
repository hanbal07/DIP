"""Evaluation script: extraction field-level accuracy.

Runs the structured extraction pipeline over the curated evaluation dataset and reports
per-field exact-match, precision/recall/F1 (non-null fields) metrics.

By default this uses the configured AI provider (``AI_PROVIDER`` env). For reproducible,
provider-independent numbers run with ``AI_PROVIDER=mock``. Actual numbers are printed --
no fabricated benchmarks.
"""
from __future__ import annotations

import asyncio
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.services.extraction import extract_structured  # noqa: E402


def normalize_for_compare(value) -> str:
    if value is None:
        return ""
    s = str(value).strip().lower()
    # Normalise punctuation/whitespace: "INV-2024-001" -> "inv-2024-001"
    return " ".join(s.split())


def exact_match(actual, expected) -> bool:
    return bool(expected) and normalize_for_compare(actual) == normalize_for_compare(expected)


async def evaluate_extraction(dataset_path: str) -> dict:
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    per_field: dict[str, dict] = {}
    doc_results = []

    for doc in dataset["documents"]:
        result = await extract_structured(doc["type"], [doc["content"]])
        data = result["data"]
        expected = doc["expected"]
        fields = doc.get("field_metrics", list(expected.keys()))

        doc_fields = []
        for field in fields:
            actual = data.get(field)
            exp = expected.get(field)
            em = exact_match(actual, exp)
            per_field.setdefault(field, {"correct": 0, "total": 0, "gold": 0})
            per_field[field]["total"] += 1
            if exp:
                per_field[field]["gold"] += 1
            if em:
                per_field[field]["correct"] += 1
            doc_fields.append(
                {"field": field, "actual": actual, "expected": exp, "exact_match": em}
            )
        doc_results.append({"id": doc["id"], "fields": doc_fields})

    # Aggregate metrics.
    total = sum(v["total"] for v in per_field.values())
    correct = sum(v["correct"] for v in per_field.values())
    gold = sum(v["gold"] for v in per_field.values())
    precision = correct / total if total else 0.0
    recall = correct / gold if gold else 0.0
    f1 = (
        2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    )

    # Per-field F1.
    per_field_metrics = {}
    for field, v in per_field.items():
        p = v["correct"] / v["gold"] if v["gold"] else 0.0
        r = v["correct"] / v["total"] if v["total"] else 0.0
        f = 2 * p * r / (p + r) if (p + r) else 0.0
        per_field_metrics[field] = {
            "precision": round(p, 3),
            "recall": round(r, 3),
            "f1": round(f, 3),
            "exact_match": round(v["correct"] / v["gold"], 3) if v["gold"] else 0.0,
        }

    report = {
        "overall": {
            "fields_attempted": total,
            "fields_with_gold": gold,
            "correct": correct,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        },
        "per_field": per_field_metrics,
        "details": doc_results,
        "provider": os.environ.get("AI_PROVIDER", "default"),
    }
    return report


async def main() -> None:
    base = pathlib.Path(__file__).resolve().parent
    report = await evaluate_extraction(str(base / "dataset.json"))
    print(json.dumps(report, indent=2, default=str))
    out = base / "results_extraction.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    asyncio.run(main())
