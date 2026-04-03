"""Structured logging configuration.

Call configure_logging() once during application startup.
All subsequent loggers created with logging.getLogger(__name__)
will emit JSON lines in production or coloured text in development.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Dict


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D102
        payload: Dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach any extra fields passed via LogRecord.__dict__
        for key in ("request_id", "job_id", "provider", "aoi_hash"):
            if key in record.__dict__:
                payload[key] = record.__dict__[key]

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class _TextFormatter(logging.Formatter):
    _COLOURS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    _RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        colour = self._COLOURS.get(record.levelname, "")
        ts = time.strftime("%H:%M:%S", time.gmtime(record.created))
        msg = record.getMessage()
        return f"{colour}{ts} [{record.levelname:<8}] {record.name}: {msg}{self._RESET}"


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """Configure root logger with the chosen level and format.

    Args:
        level: Python log level string (DEBUG, INFO, WARNING, ERROR).
        fmt:   "json" for structured JSON logs, "text" for human-readable.
    """
    formatter: logging.Formatter
    if fmt == "json":
        formatter = _JsonFormatter()
    else:
        formatter = _TextFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

    # Quieten noisy third-party loggers
    for lib in ("uvicorn.access", "celery.app.trace", "httpx"):
        logging.getLogger(lib).setLevel(logging.WARNING)
