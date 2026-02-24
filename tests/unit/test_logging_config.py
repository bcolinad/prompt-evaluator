"""Unit tests for the centralized logging configuration."""

import logging

from src.utils.logging_config import setup_logging


class TestSetupLogging:
    def test_sets_root_level(self):
        setup_logging(level="DEBUG", environment="development")
        assert logging.getLogger().level == logging.DEBUG

    def test_dev_format_uses_human_readable(self):
        setup_logging(level="INFO", environment="development")
        handler = logging.getLogger().handlers[0]
        assert "%(name)s" in handler.formatter._fmt
        assert "json" not in handler.formatter._fmt.lower()

    def test_prod_format_uses_structured(self):
        setup_logging(level="INFO", environment="production")
        handler = logging.getLogger().handlers[0]
        assert '"level"' in handler.formatter._fmt

    def test_staging_uses_structured_format(self):
        setup_logging(level="INFO", environment="staging")
        handler = logging.getLogger().handlers[0]
        assert '"level"' in handler.formatter._fmt

    def test_silences_noisy_loggers(self):
        setup_logging(level="DEBUG", environment="development")
        assert logging.getLogger("httpx").level >= logging.WARNING
        assert logging.getLogger("sqlalchemy.engine").level >= logging.WARNING
        assert logging.getLogger("langchain").level >= logging.WARNING
        assert logging.getLogger("langsmith").level >= logging.WARNING

    def test_clears_existing_handlers(self):
        root = logging.getLogger()
        root.addHandler(logging.StreamHandler())
        root.addHandler(logging.StreamHandler())
        assert len(root.handlers) >= 2
        setup_logging(level="INFO", environment="development")
        assert len(root.handlers) == 1

    def test_level_case_insensitive(self):
        setup_logging(level="warning", environment="development")
        assert logging.getLogger().level == logging.WARNING
