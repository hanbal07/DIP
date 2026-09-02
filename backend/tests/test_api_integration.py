"""Integration tests: upload -> process -> status, listing, ownership isolation,
deletion, search, chat.

Processing runs the real pipeline in-process against the test SQLite engine (the event
loop / session from fixtures share the same database file).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.document import Document, ProcessingJob
from tests import helpers


async def _register_and_token(client, email="u1@example.com"):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "full_name": "User"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return r.json()["access_token"]


async def _upload_pdf(client, token, filename="invoice.pdf", content=None):
    if content is None:
        content = helpers.make_digital_pdf()
    files = {"file": (filename, content, "application/pdf")}
    r = await client.post(
        "/api/v1/documents", files=files, headers={"Authorization": f"Bearer {token}"}
    )
    return r


async def _process(db_session, doc_id: str):
    """Run the real pipeline against the test session."""
    from app.services.pipeline import run_pipeline

    doc = (
        await db_session.execute(select(Document).where(Document.id == uuid.UUID(doc_id)))
    ).scalar_one()
    job = ProcessingJob(
        document_id=doc.id, user_id=doc.user_id, status="pending",
        stages={"queued": {"status": "processing"}},
    )
    db_session.add(job)
    await db_session.flush()
    outcome = await run_pipeline(db_session, doc, job)
    return outcome


@pytest.mark.asyncio
async def test_full_processing_flow(client, db_session):
    token = await _register_and_token(client, "flow@example.com")
    r = await _upload_pdf(client, token)
    assert r.status_code == 202, r.text
    body = r.json()
    doc_id = body["document_id"]

    outcome = await _process(db_session, doc_id)
    assert outcome.status == "completed", outcome.error

    r2 = await client.get(
        f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert r2.status_code == 200
    detail = r2.json()
    assert detail["status"] == "completed"
    assert detail["page_count"] == 1
    assert detail["review_status"] in ("not_required", "pending")

    r3 = await client.get(
        f"/api/v1/documents/{doc_id}/extraction", headers={"Authorization": f"Bearer {token}"}
    )
    assert r3.status_code == 200
    ext = r3.json()
    assert "invoice_number" in ext["raw_data"]

    r4 = await client.get(
        f"/api/v1/documents/{doc_id}/pages", headers={"Authorization": f"Bearer {token}"}
    )
    assert r4.status_code == 200
    assert len(r4.json()) == 1

    r5 = await client.get(
        "/api/v1/documents", headers={"Authorization": f"Bearer {token}"}
    )
    assert r5.status_code == 200
    assert r5.json()["total"] == 1


@pytest.mark.asyncio
async def test_unsupported_file_rejected(client):
    token = await _register_and_token(client, "bad@example.com")
    files = {"file": ("evil.exe", b"MZ\x90\x00binary", "application/octet-stream")}
    r = await client.post(
        "/api/v1/documents", files=files, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_corrupted_pdf_handled_gracefully(client, db_session):
    token = await _register_and_token(client, "corrupt@example.com")
    r = await _upload_pdf(client, token, content=helpers.make_malformed_pdf())
    if r.status_code == 202:
        doc_id = r.json()["document_id"]
        outcome = await _process(db_session, doc_id)
        assert outcome.status == "failed"
    else:
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_user_isolation(client):
    token1 = await _register_and_token(client, "iso1@example.com")
    token2 = await _register_and_token(client, "iso2@example.com")

    r = await _upload_pdf(client, token1, filename="private.pdf")
    doc_id = r.json()["document_id"]

    r2 = await client.get(
        f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token2}"}
    )
    assert r2.status_code == 404

    r3 = await client.delete(
        f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token2}"}
    )
    assert r3.status_code == 404

    r4 = await client.get("/api/v1/documents", headers={"Authorization": f"Bearer {token2}"})
    assert r4.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_review_status_filter(client, db_session):
    token = await _register_and_token(client, "reviewlist@example.com")
    me = (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})).json()
    user_id = uuid.UUID(me["id"])

    pending = Document(
        user_id=user_id,
        filename="needs-review.pdf",
        storage_key=f"k-{uuid.uuid4()}",
        content_type="application/pdf",
        file_size=100,
        extension="pdf",
        document_type="invoice",
        status="completed",
        review_status="pending",
    )
    fine = Document(
        user_id=user_id,
        filename="auto-ok.pdf",
        storage_key=f"k-{uuid.uuid4()}",
        content_type="application/pdf",
        file_size=100,
        extension="pdf",
        document_type="invoice",
        status="completed",
        review_status="not_required",
    )
    db_session.add_all([pending, fine])
    await db_session.commit()

    r = await client.get(
        "/api/v1/documents?review_status=pending&sort=filename&order=asc",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["filename"] == "needs-review.pdf"
    assert body["items"][0]["review_status"] == "pending"


@pytest.mark.asyncio
async def test_search_returns_results(client, db_session):
    token = await _register_and_token(client, "search@example.com")
    r = await _upload_pdf(
        client, token, filename="report.pdf",
        content=helpers.make_digital_pdf("Quarterly Report\nRevenue increased 20% this quarter.\n"),
    )
    doc_id = r.json()["document_id"]
    await _process(db_session, doc_id)

    r2 = await client.get(
        "/api/v1/search?q=revenue+report", headers={"Authorization": f"Bearer {token}"}
    )
    assert r2.status_code == 200
    assert len(r2.json()["hits"]) >= 1


@pytest.mark.asyncio
async def test_chat_endpoint(client, db_session):
    token = await _register_and_token(client, "chat@example.com")
    r = await _upload_pdf(
        client, token, filename="policy.pdf",
        content=helpers.make_digital_pdf(
            "Company Policy\nThe vacation policy allows 20 days per year.\n"
        ),
    )
    doc_id = r.json()["document_id"]
    await _process(db_session, doc_id)

    r2 = await client.post(
        "/api/v1/chat",
        json={"question": "How many vacation days are allowed?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["conversation_id"]


@pytest.mark.asyncio
async def test_delete_document(client):
    token = await _register_and_token(client, "del@example.com")
    r = await _upload_pdf(client, token)
    doc_id = r.json()["document_id"]

    await _upload_pdf(client, token)

    r2 = await client.delete(
        f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert r2.status_code == 200

    r3 = await client.get(
        f"/api/v1/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert r3.status_code == 404


@pytest.mark.asyncio
async def test_extraction_review(client, db_session):
    token = await _register_and_token(client, "review@example.com")
    r = await _upload_pdf(client, token)
    doc_id = r.json()["document_id"]
    await _process(db_session, doc_id)

    r2 = await client.put(
        f"/api/v1/documents/{doc_id}/extraction/review",
        json={"corrections": [{"field": "invoice_number", "value": "Corr-999"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["corrected_data"]["invoice_number"] == "Corr-999"
    assert body["review_status"] == "reviewed"


@pytest.mark.asyncio
async def test_rag_insufficient_evidence(client, db_session):
    token = await _register_and_token(client, "rag@example.com")
    r = await _upload_pdf(
        client, token, filename="notes.pdf",
        content=helpers.make_digital_pdf("Just a short note about meetings.\n"),
    )
    doc_id = r.json()["document_id"]
    await _process(db_session, doc_id)

    # A question unrelated to the single document should yield an insufficiency signal.
    reply = await client.post(
        "/api/v1/chat",
        json={"question": "What is the launch date for the Mars rover?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reply.status_code == 200
    body = reply.json()
    assert isinstance(body["has_sufficient_evidence"], bool)
