"""Centralized logging configuration for the application."""

from __future__ import annotations

import logging
import sys

_DEV_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_PROD_FORMAT = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}'

_NOISY_LOGGERS = [
    "httpx",
    "httpcore",
    "sqlalchemy.engine",
    "langchain",
    "langsmith",
    "langchain_core",
    "anthropic",
    "ollama",
]


def setup_logging(level: str = "INFO", environment: str = "development") -> None:
    """Configure application-wide logging.

    Args:
        level: Root log level (e.g. "DEBUG", "INFO", "WARNING").
        environment: One of "development", "staging", "production".
            Dev uses human-readable format; others use structured JSON-like format.
    """
    fmt = _DEV_FORMAT if environment == "development" else _PROD_FORMAT

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.setLevel(level.upper())

    # Remove existing handlers to avoid duplicate output
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for logger_name in _NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
