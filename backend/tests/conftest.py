"""Shared test fixtures.

Tests use an in-memory/file SQLite database (aiosqlite) and the deterministic mock AI
provider so the suite requires NO external services. pgvector-specific raw SQL retrieval
is exercised through a lightweight stub in integration tests.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Ensure package importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Must be set before importing app modules so config resolves to test mode.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("AI_PROVIDER", "mock")
os.environ.setdefault("OCR_ENGINE", "mock")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MAX_UPLOAD_SIZE_BYTES", str(5 * 1024 * 1024))

from sqlalchemy import event  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base  # noqa: E402
from app import models  # noqa: F401,E402


@pytest_asyncio.fixture
async def db_engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest.fixture
def anyio_backend():
    return "asyncio"


# --------------------------------------------------------------------------- API app


@pytest_asyncio.fixture
async def client(db_engine):
    """TestClient-backed app with DB dependency overridden to the test SQLite engine."""
    from httpx import ASGITransport, AsyncClient
    from app.db.base import get_db
    from app.main import create_app

    Session = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with Session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
