"""Unit tests for config settings and env var propagation."""

from __future__ import annotations

import os
from unittest.mock import patch

from src.config import LLMProvider, Settings, get_settings


class TestLLMProviderEnum:
    def test_ollama_enum_exists(self):
        assert LLMProvider.OLLAMA == "ollama"

    def test_all_providers(self):
        assert {p.value for p in LLMProvider} == {"anthropic", "google", "ollama"}


class TestOllamaSettings:
    def test_default_ollama_chat_model(self):
        s = Settings.__new__(Settings)
        # Access class-level defaults
        assert Settings.model_fields["ollama_chat_model"].default == "qwen3:4b"

    def test_default_ollama_num_predict(self):
        assert Settings.model_fields["ollama_num_predict"].default == 16384

    def test_default_ollama_request_timeout(self):
        assert Settings.model_fields["ollama_request_timeout"].default == 120.0


class TestGetSettingsEnvPropagation:
    def test_propagates_langchain_tracing_v2(self):
        """get_settings() should set LANGCHAIN_TRACING_V2 in os.environ."""
        env = {}
        with patch.dict(os.environ, env, clear=True), \
             patch("src.config.Settings") as MockSettings:
            s = Settings.__new__(Settings)
            object.__setattr__(s, "langchain_tracing_v2", True)
            object.__setattr__(s, "langchain_api_key", "test-key")
            object.__setattr__(s, "langchain_project", "test-project")
            MockSettings.return_value = s
            get_settings.cache_clear()

            get_settings()

            assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
            assert os.environ.get("LANGCHAIN_API_KEY") == "test-key"
            assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"
        get_settings.cache_clear()

    def test_does_not_overwrite_existing_env_vars(self):
        """setdefault should not overwrite pre-existing env vars."""
        env = {
            "LANGCHAIN_TRACING_V2": "false",
            "LANGCHAIN_API_KEY": "existing-key",
            "LANGCHAIN_PROJECT": "existing-project",
        }
        with patch.dict(os.environ, env, clear=True), \
             patch("src.config.Settings") as MockSettings:
            s = Settings.__new__(Settings)
            object.__setattr__(s, "langchain_tracing_v2", True)
            object.__setattr__(s, "langchain_api_key", "new-key")
            object.__setattr__(s, "langchain_project", "new-project")
            MockSettings.return_value = s
            get_settings.cache_clear()

            get_settings()

            assert os.environ["LANGCHAIN_TRACING_V2"] == "false"
            assert os.environ["LANGCHAIN_API_KEY"] == "existing-key"
            assert os.environ["LANGCHAIN_PROJECT"] == "existing-project"
        get_settings.cache_clear()

    def test_skips_api_key_when_none(self):
        """When langchain_api_key is None, it should not be set."""
        env = {}
        with patch.dict(os.environ, env, clear=True), \
             patch("src.config.Settings") as MockSettings:
            s = Settings.__new__(Settings)
            object.__setattr__(s, "langchain_tracing_v2", False)
            object.__setattr__(s, "langchain_api_key", None)
            object.__setattr__(s, "langchain_project", "test-project")
            MockSettings.return_value = s
            get_settings.cache_clear()

            get_settings()

            assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"
            assert "LANGCHAIN_API_KEY" not in os.environ
            assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"
        get_settings.cache_clear()

    def test_skips_langchain_project_when_none(self):
        """When langchain_project is None, it should not crash or be set."""
        env = {}
        with patch.dict(os.environ, env, clear=True), \
             patch("src.config.Settings") as MockSettings:
            s = Settings.__new__(Settings)
            object.__setattr__(s, "langchain_tracing_v2", False)
            object.__setattr__(s, "langchain_api_key", None)
            object.__setattr__(s, "langchain_project", None)
            MockSettings.return_value = s
            get_settings.cache_clear()

            get_settings()

            assert "LANGCHAIN_PROJECT" not in os.environ
        get_settings.cache_clear()
