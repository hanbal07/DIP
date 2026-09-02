"""Structured logging configuration.

Logs are JSON-formatted in production for easy collection, and human-readable in
development. We never log document contents or secrets.
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """Minimal JSON log formatter for structured observability."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    # Avoid duplicate handlers on reload.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if settings.environment == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-7s %(name)s - %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    root.addHandler(handler)

    # Tame noisy third-party loggers.
    logging.getLogger("passlib").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
