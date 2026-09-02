"""pgvector integration for SQLAlchemy.

Provides a `Vector` user-defined type so `document_chunks.embedding` can be declared in the
ORM model. The HNSW index is created in the Alembic migration (better for reproducible
schema control) rather than inline. At import time we keep the dependency optional: the
app only requires pgvector when the embedding column is actually used by pgvector-specific
SQL in the repository layer, so tests using SQLite can run without it.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    """pgvector `vector(n)` column type."""

    cache_ok = True

    def __init__(self, dim: int | None = None):
        self.dim = dim

    def get_col_spec(self, **kw: Any) -> str:
        if self.dim is not None:
            return f"VECTOR({self.dim})"
        return "VECTOR"

    def bind_processor(self, dialect: Any) -> Any:
        def process(value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, list):
                return "[" + ",".join(str(float(v)) for v in value) + "]"
            return value

        return process

    def result_processor(self, dialect: Any, coltype: Any) -> Any:
        def process(value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, str):
                return [float(x) for x in value.strip("[]").split(",")]
            return value

        return process

    class comparator_factory(UserDefinedType.Comparator):
        # Only defined here for reference; distance operators are constructed with raw
        # SQL in the repository layer (<=> for cosine) to keep the dependency light.
        pass
