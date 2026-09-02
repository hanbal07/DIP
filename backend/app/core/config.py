"""Application configuration loaded from environment variables.

Secrets and credentials are read ONLY from the environment (or `.env` file loaded by
pydantic-settings in development). Nothing sensitive is hardcoded here.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the backend.

    Every field maps to an environment variable; see `.env.example` for the full
    documented list with safe placeholder values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Core ---
    app_name: str = "Document Intelligence Platform"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # --- Security ---
    #: Secret used to sign JWT access tokens. MUST be overridden in production.
    secret_key: str = "change-me-in-production-please-use-a-long-random-string"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    algorithm: str = "HS256"

    # --- Database ---
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/document_intelligence"
    )
    #: Synchronous URL for Alembic migrations (asyncpg cannot run migrations).
    database_url_sync: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/document_intelligence"
    )
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # --- Redis / tasks ---
    redis_url: str = "redis://localhost:6379/0"
    task_queue_name: str = "document-processing"

    # --- File storage ---
    upload_dir: str = "storage/uploads"
    export_dir: str = "storage/exports"
    max_upload_size_bytes: int = 50 * 1024 * 1024  # 50 MB
    max_pages: int = 100
    allowed_extensions: str = (
        "pdf,png,jpg,jpeg,tiff,tif,bmp,gif,webp,docx,doc,txt,md,rtf"
    )

    # --- Document processing / OCR ---
    ocr_engine: Literal["paddleocr", "tesseract", "mock"] = "mock"
    #: Resolution (DPI) used when rendering pages to images for OCR.
    ocr_render_dpi: int = 200
    tesseract_cmd: Optional[str] = None
    ocr_lang: str = "eng"

    # --- AI provider (configurable through env) ---
    ai_provider: Literal["openai", "anthropic", "mock"] = "mock"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    embedding_dimensions: int = 1536

    # --- Rate limiting (simple, per-endpoint) ---
    rate_limit_rpm: int = 60
    rate_limit_chat_rpm: int = 15

    # --- Provider timeouts / retries ---
    provider_timeout_seconds: float = 60.0
    provider_max_retries: int = 3

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    # --- Monitoring ---
    log_level: str = "INFO"

    # ------------------------------------------------------------------ helpers

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {e.strip().lstrip(".").lower() for e in self.allowed_extensions.split(",")}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
