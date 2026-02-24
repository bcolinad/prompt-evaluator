"""Unit tests for the LLM factory with Google → Anthropic → Ollama cascade."""

from unittest.mock import MagicMock, patch

import pytest

from src.utils.llm_factory import (
    _GOOGLE_KEY_PATH,
    _try_anthropic,
    _try_google,
    _try_ollama,
    get_llm,
)

# ---------------------------------------------------------------------------
# _try_google tests
# ---------------------------------------------------------------------------


class TestTryGoogle:
    @patch("src.config.get_settings")
    @patch("src.utils.llm_factory._GOOGLE_KEY_PATH")
    def test_returns_none_when_key_file_missing(self, mock_path, mock_settings):
        mock_path.exists.return_value = False
        result = _try_google()
        assert result is None

    @patch("src.config.get_settings")
    @patch("src.utils.llm_factory.ChatGoogleGenerativeAI", create=True)
    @patch("src.utils.llm_factory._GOOGLE_KEY_PATH")
    def test_returns_llm_when_key_exists(self, mock_path, mock_cls, mock_settings):
        mock_path.exists.return_value = True
        mock_path.__str__ = lambda _: "/fake/google-key.json"
        settings = MagicMock()
        settings.google_model = "gemini-2.5-flash"
        settings.google_project = "test-project"
        settings.google_location = "us-central1"
        settings.llm_temperature = 0.0
        mock_settings.return_value = settings

        # Patch the import inside _try_google
        mock_llm = MagicMock()
        with patch(
            "src.utils.llm_factory.ChatGoogleGenerativeAI",
            create=True,
        ) as patched_import:
            # We need to patch the import at module level within the function
            pass

        # Simpler: patch the entire function's import path
        with patch.dict("sys.modules", {"langchain_google_genai": MagicMock()}), patch(
            "langchain_google_genai.ChatGoogleGenerativeAI",
            return_value=mock_llm,
        ):
            result = _try_google()
            assert result is not None

    @patch("src.config.get_settings")
    @patch("src.utils.llm_factory._GOOGLE_KEY_PATH")
    def test_returns_none_on_initialization_error(self, mock_path, mock_settings):
        mock_path.exists.return_value = True
        mock_path.__str__ = lambda _: "/fake/google-key.json"
        settings = MagicMock()
        settings.google_model = "gemini-2.5-flash"
        settings.google_project = "test-project"
        settings.google_location = "us-central1"
        settings.llm_temperature = 0.0
        mock_settings.return_value = settings

        with patch.dict("sys.modules", {"langchain_google_genai": MagicMock()}) as _, patch(
            "langchain_google_genai.ChatGoogleGenerativeAI",
            side_effect=Exception("auth failed"),
        ):
            result = _try_google()
            assert result is None


# ---------------------------------------------------------------------------
# _try_anthropic tests
# ---------------------------------------------------------------------------


class TestTryAnthropic:
    @patch("src.config.get_settings")
    def test_returns_none_when_no_api_key(self, mock_settings):
        settings = MagicMock()
        settings.anthropic_api_key = None
        mock_settings.return_value = settings
        result = _try_anthropic()
        assert result is None

    @patch("src.config.get_settings")
    def test_returns_none_when_empty_api_key(self, mock_settings):
        settings = MagicMock()
        settings.anthropic_api_key = ""
        mock_settings.return_value = settings
        result = _try_anthropic()
        assert result is None

    @patch("src.config.get_settings")
    def test_returns_llm_when_api_key_set(self, mock_settings):
        settings = MagicMock()
        settings.anthropic_api_key = "sk-ant-test-key"
        settings.anthropic_model = "claude-sonnet-4-20250514"
        settings.llm_temperature = 0.0
        settings.llm_max_tokens = 4096
        mock_settings.return_value = settings

        with patch("langchain_anthropic.ChatAnthropic", return_value=MagicMock()):
            result = _try_anthropic()
            assert result is not None

    @patch("src.config.get_settings")
    def test_passes_correct_params(self, mock_settings):
        settings = MagicMock()
        settings.anthropic_api_key = "sk-ant-test-key"
        settings.anthropic_model = "claude-sonnet-4-20250514"
        settings.llm_temperature = 0.3
        settings.llm_max_tokens = 8192
        mock_settings.return_value = settings

        with patch("langchain_anthropic.ChatAnthropic") as mock_cls:
            mock_cls.return_value = MagicMock()
            _try_anthropic()

            mock_cls.assert_called_once_with(
                model="claude-sonnet-4-20250514",
                api_key="sk-ant-test-key",
                temperature=0.3,
                max_tokens=8192,
            )


# ---------------------------------------------------------------------------
# _try_ollama tests
# ---------------------------------------------------------------------------


class TestTryOllama:
    @patch("src.config.get_settings")
    def test_returns_none_when_no_base_url(self, mock_settings):
        settings = MagicMock()
        settings.ollama_base_url = None
        mock_settings.return_value = settings
        result = _try_ollama()
        assert result is None

    @patch("src.config.get_settings")
    def test_returns_none_when_empty_base_url(self, mock_settings):
        settings = MagicMock()
        settings.ollama_base_url = ""
        mock_settings.return_value = settings
        result = _try_ollama()
        assert result is None

    @patch("src.config.get_settings")
    def test_returns_llm_when_configured(self, mock_settings):
        settings = MagicMock()
        settings.ollama_base_url = "http://localhost:11434"
        settings.ollama_chat_model = "qwen3:4b"
        settings.llm_temperature = 0.0
        settings.ollama_num_predict = 16384
        settings.ollama_request_timeout = 120.0
        mock_settings.return_value = settings

        with patch("langchain_ollama.ChatOllama", return_value=MagicMock()):
            result = _try_ollama()
            assert result is not None

    @patch("src.config.get_settings")
    def test_passes_correct_params(self, mock_settings):
        settings = MagicMock()
        settings.ollama_base_url = "http://ollama:11434"
        settings.ollama_chat_model = "qwen3:4b"
        settings.llm_temperature = 0.0
        settings.ollama_num_predict = 8192
        settings.ollama_request_timeout = 60.0
        mock_settings.return_value = settings

        with patch("langchain_ollama.ChatOllama") as mock_cls:
            mock_cls.return_value = MagicMock()
            _try_ollama()

            mock_cls.assert_called_once_with(
                model="qwen3:4b",
                base_url="http://ollama:11434",
                temperature=0.0,
                num_predict=8192,
                timeout=60.0,
            )

    @patch("src.config.get_settings")
    def test_returns_none_on_initialization_error(self, mock_settings):
        settings = MagicMock()
        settings.ollama_base_url = "http://localhost:11434"
        settings.ollama_chat_model = "qwen3:4b"
        settings.llm_temperature = 0.0
        settings.ollama_num_predict = 16384
        settings.ollama_request_timeout = 120.0
        mock_settings.return_value = settings

        with patch(
            "langchain_ollama.ChatOllama",
            side_effect=Exception("connection error"),
        ):
            result = _try_ollama()
            assert result is None


# ---------------------------------------------------------------------------
# get_llm tests
# ---------------------------------------------------------------------------


class TestGetLLM:
    @patch("src.utils.llm_factory._try_anthropic")
    @patch("src.utils.llm_factory._try_google")
    def test_returns_google_when_available(self, mock_google, mock_anthropic):
        mock_google.return_value = MagicMock(name="google-llm")
        result = get_llm()
        assert result == mock_google.return_value
        mock_anthropic.assert_not_called()

    @patch("src.utils.llm_factory._try_ollama")
    @patch("src.utils.llm_factory._try_anthropic")
    @patch("src.utils.llm_factory._try_google")
    def test_falls_back_to_anthropic_when_google_fails(
        self, mock_google, mock_anthropic, mock_ollama
    ):
        mock_google.return_value = None
        mock_anthropic.return_value = MagicMock(name="anthropic-llm")
        result = get_llm()
        assert result == mock_anthropic.return_value
        mock_ollama.assert_not_called()

    @patch("src.utils.llm_factory._try_ollama")
    @patch("src.utils.llm_factory._try_anthropic")
    @patch("src.utils.llm_factory._try_google")
    def test_falls_back_to_ollama_when_cloud_fails(
        self, mock_google, mock_anthropic, mock_ollama
    ):
        mock_google.return_value = None
        mock_anthropic.return_value = None
        mock_ollama.return_value = MagicMock(name="ollama-llm")
        result = get_llm()
        assert result == mock_ollama.return_value

    @patch("src.utils.llm_factory._try_ollama")
    @patch("src.utils.llm_factory._try_anthropic")
    @patch("src.utils.llm_factory._try_google")
    def test_raises_when_all_three_fail(
        self, mock_google, mock_anthropic, mock_ollama
    ):
        mock_google.return_value = None
        mock_anthropic.return_value = None
        mock_ollama.return_value = None

        with pytest.raises(RuntimeError, match="No LLM provider available"):
            get_llm()

    @patch("src.utils.llm_factory._try_ollama")
    @patch("src.utils.llm_factory._try_anthropic")
    @patch("src.utils.llm_factory._try_google")
    def test_error_message_includes_setup_instructions(
        self, mock_google, mock_anthropic, mock_ollama
    ):
        mock_google.return_value = None
        mock_anthropic.return_value = None
        mock_ollama.return_value = None

        with pytest.raises(RuntimeError) as exc_info:
            get_llm()

        msg = str(exc_info.value)
        assert "Google Vertex AI" in msg
        assert "google-key.json" in msg
        assert "Anthropic Claude" in msg
        assert "ANTHROPIC_API_KEY" in msg
        assert "console.anthropic.com" in msg
        assert "Ollama" in msg
        assert "OLLAMA_BASE_URL" in msg

    @patch("src.utils.llm_factory._try_ollama")
    def test_explicit_ollama_provider(self, mock_ollama):
        mock_ollama.return_value = MagicMock(name="ollama-llm")
        result = get_llm(provider="ollama")
        assert result == mock_ollama.return_value

    @patch("src.utils.llm_factory._try_ollama")
    def test_explicit_ollama_raises_on_failure(self, mock_ollama):
        mock_ollama.return_value = None
        with pytest.raises(RuntimeError, match="Ollama initialization failed"):
            get_llm(provider="ollama")

    def test_google_key_path_points_to_agent_nodes(self):
        assert _GOOGLE_KEY_PATH.name == "google-key.json"
        assert "agent" in str(_GOOGLE_KEY_PATH)
        assert "nodes" in str(_GOOGLE_KEY_PATH)
