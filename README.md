# Document Intelligence Platform

A production-style, end-to-end AI document processing platform. Upload PDFs and images,
and the system validates, classifies, OCRs, extracts structured data (per document type),
embeds, indexes, and exposes everything through an ownership-isolated REST API — plus a
Next.js dashboard with semantic search and RAG chat with citations.

```
                         ┌─────────────────────────────────────────────┐
                         │                 Next.js 14                   │
                         │   Dashboard · Documents · Detail · Search    │
                         │   Ask AI · Review · Settings                 │
                         │   (React 18 + Tailwind + shadcn)             │
                         └───────────────────┬─────────────────────────┘
                                             │  HTTPS / REST (JSON)
                                             ▼
                         ┌─────────────────────────────────────────────┐
                         │             FastAPI backend  /api/v1         │
                         │  auth · documents · review · search · chat    │
                         │  health  (+ rate limits, JWT, audit log,      │
                         │            per-user row-level isolation)      │
                         └───────┬──────────────────┬───────────────────┘
                                 │                  │
                 upload → job    │                  │  RAG retrieval (pgvector)
                                 ▼                  ▼
                         ┌─────────────────────────────────────────────┐
                         │   Processing pipeline (worker / in-process)  │
                         │                                                │
                         │  validate → inspect → classify → pages        │
                         │  → text/OCR → sections → tables               │
                         │  → typed extraction → chunk → embed → persist │
                         └─────────────────────────────────────────────┘
                                 │                    │
                                 ▼                    ▼
                         ┌────────────────┐   ┌────────────────────────┐
                         │  PostgreSQL 16 │   │   Redis 7 · Celery      │
                         │  + pgvector    │   │   (jobs, retries)       │
                         │  (chunks, HNSW)│   └────────────────────────┘
                         └────────────────┘
                    AI providers: OpenAI / Anthropic / mock (deterministic)
                    OCR engines:  PaddleOCR / Tesseract / mock
```

## Features

- **Secure multi-user** — password hashing (argon2 via passlib/bcrypt), short-lived JWTs,
  per-user row-level isolation on every endpoint (documents, pages, chunks, entities,
  tables, conversations), deletion cascades through all derived data, audit log.
- **Robust uploads** — 20+ allowed formats, MIME sniffing + extension checks, size/page
  limits, non-guessable storage keys, and clean rejection of unsupported/corrupted files.
- **Deterministic pipelines** — accepts only supported document types, retries individual
  stages, detects OCR-vs-digital text, and is safe to re-run (idempotent).
- **Typed extraction** — 9 document schemas (invoice, receipt, resume, contract, report,
  research_paper, form, certificate, unknown) with per-field source references; model
  outputs and human corrections are stored separately (`raw_data` vs `corrected_data`).
- **Human review** — low-confidence extractions are flagged (`review_status = pending`)
  and collected in a dedicated **Review** queue; corrections are saved through the review
  endpoint, kept separate from raw model output, and audited.
- **Semantic search** — ownership-filtered cosine/pgvector search over embeddings with
  default-quality scoring and snippets.
- **RAG chat** — per-document **and** cross-document ("Ask AI") chat with citations on
  every answer, history-aware multi-turn, prompt-injection defense (prioritizes retrieved
  evidence over instructions), and answers that clearly say when evidence is insufficient.
- **Background jobs** — Celery worker (or in-process bridge for tests / local dev) with
  per-stage status, progress, retry, and configuration via env.
- **Packaged for deployment** — Docker Compose (Postgres pgvector, Redis, API, worker,
  frontend), Alembic migrations, health endpoints, and a CI workflow.

## Repository layout

```
.
├── backend/                 # Python FastAPI application
│   ├── app/
│   │   ├── api/             #  auth, documents, search, chat, health, deps
│   │   ├── ai/              #  providers (openai/anthropic/mock), client, schemas
│   │   ├── core/            #  config, logging, security, tasks, rate_limit
│   │   ├── db/              #  async session factory
│   │   ├── models/          #  SQLAlchemy models + Vector type
│   │   ├── schemas/         #  Pydantic schemas
│   │   └── services/        #  pipeline + all processing services
│   ├── alembic/             #  migrations (pgvector + HNSW)
│   ├── tests/               #  48 pytest tests
│   ├── evaluation/          #  dataset + extraction/RAG evals
│   ├── Dockerfile / Dockerfile.worker
│   └── requirements*.txt
├── frontend/                # Next.js 14 App Router application
│   ├── app/                 #  pages (auth, dashboard, documents, detail,
│   │                        #   search, ask, review, settings)
│   ├── components/          #  UI kit + feature components
│   └── lib/                 #  API client, types, auth context, utils
├── docker/                  # init-db.sql
└── docker-compose.yml
```

## Backend reference

Full backend documentation (setup, architecture, API, security model, testing) lives in
[`backend/README.md`](backend/README.md).

## Quick start (local, no Docker)

### 1. Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt   # Windows
# . venv/bin/pip install -r requirements.txt      # Linux/macOS
```

Copy root `.env.example` to a `.env` file and set `DATABASE_URL` for a local
PostgreSQL + pgvector instance, or run tests with SQLite (no DB needed):

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest -q          # 47 tests (SQLite, mock AI/OCR)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

By default the app uses `mock` AI/OCR providers so it works without external keys.
Set `AI_PROVIDER=openai` (+ `OPENAI_API_KEY`) and `OCR_ENGINE=paddleocr|tesseract`
for real inference. **Production mode refuses to fall back to mock.**

> **Verification note:** this release candidate is verified by 48 passing backend tests
> and a strict static review of the frontend. The frontend build itself is executed and
> verified by the CI workflow (`frontend` job), because a local Node.js toolchain was not
> available on the machine used to author this release.

### 2. Frontend (needs Node.js 20)

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api/v1`).

### 3. Docker

```bash
cp .env.example .env
docker compose up --build
# API:        http://localhost:8000/api/v1
# Frontend:   http://localhost:3000
```

## Configuration

Every setting is via environment variables — see [`.env.example`](.env.example).
Highlights:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing secret (must be random in prod) |
| `DATABASE_URL` / `DATABASE_URL_SYNC` | Async app / sync alembic DSNs |
| `AI_PROVIDER` | `openai` \| `anthropic` \| `mock` |
| `OCR_ENGINE` | `paddleocr` \| `tesseract` \| `mock` |
| `EMBEDDING_DIMENSIONS` | Must match the embedding model (default 1536) |
| `MAX_UPLOAD_SIZE_BYTES` / `MAX_PAGES` | Upload limits |
| `RATE_LIMIT_RPM` / `RATE_LIMIT_CHAT_RPM` | Per-user rate limits |

## Testing

- **Backend:** `cd backend && .\.venv\Scripts\python.exe -m pytest -q` (48 tests)
  covering validation, extraction schemas, chunking, entities, providers, auth,
  full API integration (upload → process → search → chat → review → delete),
  review-status filtering, and pipeline safety (retry idempotency, cross-user
  isolation, prompt injection).
- **Frontend:** `cd frontend && npm run lint && npm run typecheck && npm test`
  (requires Node.js 20; also run in CI).

## Evaluation

`backend/evaluation/` contains a labeled dataset and scripts:

```bash
cd backend
.\.venv\Scripts\python.exe evaluation\evaluate_extraction.py   # extraction accuracy
.\.venv\Scripts\python.exe evaluation\evaluate_rag.py          # RAG answer quality
```

With the `mock` provider these produce deterministic but low ceiling numbers
(`results_extraction.json`). Run with a configured LLM for real metrics.

## Security model

- Passwords hashed with argon2/bcrypt; tokens are short-lived JWTs.
- Every query filters by `user_id`; conversations validate document ownership and
  silently ignore unowned document ids (no existence leaks).
- Uploads are validated by extension *and* content sniffing; paths are generated,
  never client-controlled.
- RAG retrieval only returns the current user's chunks; chat rejects documents the user
  no longer owns.
- Rate limiting on all endpoints and a stricter limit on chat.
- No secrets in the repo — everything comes from the environment.

## License / status

Demonstration implementation. Not a substitute for compliance review before production
use of real personal or financial data.

### GitHub Pages / live demo

This is a full-stack application (API + worker + Postgres/pgvector + Redis). A faithful
GitHub Pages demo is **not provided**: static Pages hosting cannot run a backend, and
switching the Next.js app to static `output: export` would break its production
`standalone` Docker deployment. Deploy the project with Docker Compose as documented
above, or host the API separately and point the frontend's `NEXT_PUBLIC_API_URL` at it.