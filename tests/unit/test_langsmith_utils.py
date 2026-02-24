"""Unit tests for LangSmith utilities."""

from unittest.mock import MagicMock, patch

from src.utils.langsmith_utils import get_langsmith_client, score_run


class TestGetLangsmithClient:
    @patch("src.config.get_settings")
    def test_returns_none_when_tracing_disabled(self, mock_settings):
        settings = MagicMock()
        settings.langchain_tracing_v2 = False
        mock_settings.return_value = settings

        assert get_langsmith_client() is None

    @patch("src.config.get_settings")
    def test_returns_none_when_missing_api_key(self, mock_settings):
        settings = MagicMock()
        settings.langchain_tracing_v2 = True
        settings.langchain_api_key = None
        mock_settings.return_value = settings

        assert get_langsmith_client() is None

    @patch("src.config.get_settings")
    @patch("src.utils.langsmith_utils.Client")
    def test_returns_client_when_configured(self, mock_cls, mock_settings):
        settings = MagicMock()
        settings.langchain_tracing_v2 = True
        settings.langchain_api_key = "lsv2-test-key"
        mock_settings.return_value = settings
        mock_cls.return_value = MagicMock()

        client = get_langsmith_client()
        assert client is not None
        mock_cls.assert_called_once()


class TestScoreRun:
    @patch("src.utils.langsmith_utils.get_langsmith_client")
    def test_scores_when_client_available(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client

        score_run("run-123", "relevance", 0.85, "Good relevance")

        mock_client.create_feedback.assert_called_once_with(
            run_id="run-123",
            key="relevance",
            score=0.85,
            comment="Good relevance",
        )

    @patch("src.utils.langsmith_utils.get_langsmith_client")
    def test_noop_when_client_none(self, mock_client_fn):
        mock_client_fn.return_value = None
        score_run("run-123", "relevance", 0.85)  # Should not raise

    @patch("src.utils.langsmith_utils.get_langsmith_client")
    def test_handles_score_exception(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.create_feedback.side_effect = Exception("API error")
        mock_client_fn.return_value = mock_client

        score_run("run-123", "relevance", 0.85)  # Should not raise
