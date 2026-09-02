"""Extraction schemas for each supported document type.

New document types are added by registering a schema definition here; the classification
and extraction pipeline is otherwise unchanged. Each schema has an explicit JSON shape used
as the `example` for structured model output, plus validation logic.
"""
from __future__ import annotations

from typing import Any

SUPPORTED_DOCUMENT_TYPES = [
    "invoice",
    "receipt",
    "resume",
    "contract",
    "report",
    "research_paper",
    "form",
    "certificate",
    "unknown",
]

#: Human-friendly labels.
TYPE_LABELS = {
    "invoice": "Invoice",
    "receipt": "Receipt",
    "resume": "Resume / CV",
    "contract": "Contract",
    "report": "Report",
    "research_paper": "Research Paper",
    "form": "Form",
    "certificate": "Certificate",
    "unknown": "General / Unknown",
}


# Each value is the JSON *example* shape for the structured output of that document type.
# Fields beginning with "__" are placeholders the provider fills. `confidence` fields are
# filled by our pipeline from real signals where available — do NOT report invented scores.
SCHEMAS: dict[str, dict[str, Any]] = {
    "invoice": {
        "invoice_number": "__invoice_number",
        "vendor_name": "__vendor_name",
        "customer_name": "__customer_name",
        "invoice_date": "__invoice_date",
        "due_date": "__due_date",
        "currency": "__currency",
        "subtotal": "__amount",
        "tax": "__amount",
        "total": "__amount",
        "line_items": [
            {
                "description": "__description",
                "quantity": 1,
                "unit_price": 1.0,
                "amount": 1.0,
            }
        ],
    },
    "receipt": {
        "merchant_name": "__merchant_name",
        "receipt_number": "__receipt_number",
        "date": "__date",
        "currency": "__currency",
        "total": "__amount",
        "items": [{"description": "__description", "amount": 1.0}],
        "payment_method": "__payment_method",
    },
    "resume": {
        "candidate_name": "__candidate_name",
        "email": "__email",
        "phone": "__phone",
        "location": "__location",
        "summary": "__summary",
        "skills": ["__skill"],
        "experience": [
            {"company": "__company", "title": "__title", "start": "__date", "end": "__date"}
        ],
        "education": [{"institution": "__institution", "degree": "__degree", "year": "__year"}],
    },
    "contract": {
        "contract_title": "__contract_title",
        "parties": [{"name": "__party_name", "role": "__role"}],
        "effective_date": "__date",
        "expiration_date": "__date",
        "key_terms": ["__term"],
        "payment_terms": "__payment_terms",
        "jurisdiction": "__jurisdiction",
    },
    "report": {
        "report_title": "__report_title",
        "author": "__author",
        "date": "__date",
        "organization": "__organization",
        "summary": "__summary",
        "key_findings": ["__finding"],
        "recommendations": ["__recommendation"],
    },
    "research_paper": {
        "title": "__title",
        "authors": ["__author"],
        "publication_date": "__date",
        "abstract": "__abstract",
        "keywords": ["__keyword"],
        "publisher": "__publisher",
        "doi": "__doi",
    },
    "form": {
        "form_title": "__form_title",
        "fields": [{"name": "__field_name", "value": "__field_value"}],
        "submitter": "__submitter",
        "date": "__date",
    },
    "certificate": {
        "certificate_title": "__certificate_title",
        "issuer": "__issuer",
        "recipient": "__recipient",
        "issue_date": "__date",
        "certificate_number": "__certificate_number",
        "expiry_date": "__expiry_date",
    },
    "unknown": {
        "document_title": "__document_title",
        "author": "__author",
        "date": "__date",
        "summary": "__summary",
        "key_points": ["__key_point"],
    },
}


def get_schema(doc_type: str) -> dict[str, Any]:
    return SCHEMAS.get(doc_type, SCHEMAS["unknown"])


def schema_fields(doc_type: str) -> list[str]:
    """Top-level field names for a schema (used for UI display and review)."""
    return list(get_schema(doc_type).keys())


def validate_structured(doc_type: str, data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Basic structural validation of model output against the schema.

    Returns (cleaned_data, warning_messages). Missing keys are backfilled with None; extra
    keys are dropped. This guards against arbitrary malformed model output.
    """
    schema = get_schema(doc_type)
    cleaned: dict[str, Any] = {}
    warnings: list[str] = []
    for key, example in schema.items():
        if key not in data or data[key] is None:
            # Only warn for genuinely missing values; optional fields may legitimately be absent.
            cleaned[key] = None
        elif isinstance(example, list):
            cleaned[key] = data[key] if isinstance(data[key], list) else [data[key]]
        elif isinstance(example, (int, float)):
            try:
                cleaned[key] = (
                    float(data[key])
                    if not isinstance(example, int)
                    else (int(float(data[key])) if isinstance(data[key], (int, float, str)) and str(data[key]).replace(".", "").isdigit() else None)
                )
            except (TypeError, ValueError):
                cleaned[key] = None
                warnings.append(f"field '{key}' invalid numeric value")
        else:
            cleaned[key] = str(data[key]) if data[key] is not None else None
    return cleaned, warnings
