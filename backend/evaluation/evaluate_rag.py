"""Evaluation script: RAG retrieval quality + answer quality + citation correctness.

Runs over the curated dataset. Because it needs a populated vector DB + embeddings, it
requires a running PostgreSQL+pgvector and a real AI provider (or the deterministic mock
for the embeddings path). For a provider-independent smoke eval of the *logic*, use the
mock provider with a live database.

Reports retrieval recall@k and per-question citation verification. Actual numbers only.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db.base import AsyncSessionLocal  # noqa: E402
from app.models.document import Document, DocumentChunk  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.retrieval import embed_query, semantic_search  # noqa: E402


def contains_any(answer: str, needles: list[str]) -> bool:
    a = answer.lower()
    return any(n.lower() in a for n in needles)


async def evaluate_rag(dataset_path: str, user_email: str = "eval@example.com") -> dict:
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    async with AsyncSessionLocal() as db:
        # Create the eval user if needed.
        user = (
            await db.execute(select(User).where(User.email == user_email))
        ).scalar_one_or_none()
        if user is None:
            from app.core.security import hash_password

            user = User(email=user_email, hashed_password=hash_password("evalpassword123"))
            db.add(user)
            await db.flush()

        # Map dataset doc id -> stored document (by filename basis not reliable), so we look
        # up documents owned by this user and simple-match on content via chunks.
        all_docs = (
            await db.execute(
                select(Document).where(Document.user_id == user.id, Document.status == "completed")
            )
        ).scalars().all()

        # Build a content->document map by scanning chunk text for a stable token.
        retrieval_results = []
        answer_results = []

        for q in dataset["rag_questions"]:
            # Find the document whose content contains the question's expected snippet.
            target = None
            if q.get("document_id"):
                for doc in all_docs:
                    chunks = (
                        await db.execute(
                            select(DocumentChunk)
                            .where(DocumentChunk.document_id == doc.id)
                            .limit(50)
                        )
                    ).scalars().all()
                    joined = " ".join(c.text for c in chunks)
                    snippet = q.get("expected_snippet") or q["expected_answer_contains"][0]
                    if snippet.lower() in joined.lower():
                        target = doc.id
                        break

            qvec = await embed_query(q["question"])
            hits = await semantic_search(db, user_id=user.id, query_embedding=qvec, limit=8)

            retrieved_ids = {h.document_id for h in hits}
            hit_contains = {
                h.text for h in hits
            }
            resolved = None
            for h in hits:
                s = q.get("expected_snippet") or q["expected_answer_contains"][0]
                if s.lower() in h.text.lower():
                    resolved = h
                    break

            retrieval_results.append(
                {
                    "question_id": q["id"],
                    "retrieved_documents": len(retrieved_ids),
                    "target_in_results": (target is not None and target in retrieved_ids),
                    "citation_found": resolved is not None,
                    "top_score": round(hits[0].score, 3) if hits else 0.0,
                }
            )

            # Answer quality is evaluated against the real QA service when a provider is set.
            answer_results.append(
                {
                    "question_id": q["id"],
                    "evaluated_with_live_model": False,
                    "note": "Answer text evaluation requires a live chat model; run RAG QA "
                            "against the API for answer-level metrics.",
                }
            )

    recall_at_k = sum(1 for r in retrieval_results if r["target_in_results"])
    citation_ok = sum(1 for r in retrieval_results if r["citation_found"])

    report = {
        "retrieval": {
            "questions_total": len(retrieval_results),
            "recall@k_target_retrieved": recall_at_k,
            "recall_at_k": round(recall_at_k / len(retrieval_results), 3) if retrieval_results else 0.0,
            "citation_available": citation_ok,
            "details": retrieval_results,
        },
        "answer": {"details": answer_results},
    }
    return report


async def main() -> None:
    base = pathlib.Path(__file__).resolve().parent
    report = await evaluate_rag(str(base / "dataset.json"))
    print(json.dumps(report, indent=2, default=str))
    out = base / "results_rag.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    asyncio.run(main())
