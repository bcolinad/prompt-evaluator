"""Unit tests for the custom exception hierarchy."""

import pytest

from src.evaluator.exceptions import (
    AnalysisError,
    ConfigurationError,
    EvaluatorError,
    ImprovementError,
    LLMError,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OutputEvaluationError,
    ReportBuildError,
    ScoringError,
    format_fatal_error,
    is_fatal_llm_error,
)


class TestEvaluatorErrorHierarchy:
    """All custom exceptions inherit from EvaluatorError."""

    @pytest.mark.parametrize("exc_class", [
        LLMError,
        AnalysisError,
        ScoringError,
        ImprovementError,
        OutputEvaluationError,
        ReportBuildError,
        ConfigurationError,
        OllamaConnectionError,
        OllamaModelNotFoundError,
    ])
    def test_subclass_of_evaluator_error(self, exc_class: type):
        assert issubclass(exc_class, EvaluatorError)

    @pytest.mark.parametrize("exc_class", [
        EvaluatorError,
        LLMError,
        AnalysisError,
        ScoringError,
        ImprovementError,
        OutputEvaluationError,
        ReportBuildError,
        ConfigurationError,
        OllamaConnectionError,
        OllamaModelNotFoundError,
    ])
    def test_subclass_of_exception(self, exc_class: type):
        assert issubclass(exc_class, Exception)


class TestEvaluatorErrorContext:
    def test_default_context_is_empty_dict(self):
        err = EvaluatorError("boom")
        assert err.context == {}

    def test_custom_context_stored(self):
        ctx = {"node": "analyzer", "input_length": 500}
        err = EvaluatorError("failed", context=ctx)
        assert err.context == ctx

    def test_message_accessible_via_str(self):
        err = EvaluatorError("something broke")
        assert str(err) == "something broke"

    def test_context_on_subclass(self):
        ctx = {"model": "claude"}
        err = LLMError("timeout", context=ctx)
        assert err.context == ctx
        assert str(err) == "timeout"

    def test_raise_and_catch_as_evaluator_error(self):
        with pytest.raises(EvaluatorError):
            raise ScoringError("bad score")

    def test_raise_and_catch_specific(self):
        with pytest.raises(AnalysisError):
            raise AnalysisError("parse failed")


class TestOllamaExceptions:
    """Ollama-specific exception classes inherit from LLMError."""

    def test_ollama_connection_error_inherits_from_llm_error(self):
        assert issubclass(OllamaConnectionError, LLMError)

    def test_ollama_model_not_found_inherits_from_llm_error(self):
        assert issubclass(OllamaModelNotFoundError, LLMError)

    def test_ollama_connection_error_context(self):
        ctx = {"url": "http://localhost:11434"}
        err = OllamaConnectionError("connection refused", context=ctx)
        assert err.context == ctx
        assert str(err) == "connection refused"

    def test_ollama_model_not_found_context(self):
        err = OllamaModelNotFoundError("model not found: qwen3:4b")
        assert str(err) == "model not found: qwen3:4b"


class TestFatalErrorDetection:
    """Tests for is_fatal_llm_error and format_fatal_error with Ollama patterns."""

    @pytest.mark.parametrize("error_msg", [
        "model not found",
        "connection refused",
        "failed to connect",
    ])
    def test_ollama_fatal_patterns_detected(self, error_msg: str):
        exc = Exception(error_msg)
        assert is_fatal_llm_error(exc) is True

    def test_model_not_found_format(self):
        exc = Exception("model not found: qwen3:4b")
        msg = format_fatal_error(exc)
        assert "Model Not Found" in msg
        assert "ollama pull" in msg

    def test_connection_refused_format(self):
        exc = Exception("connection refused to http://localhost:11434")
        msg = format_fatal_error(exc)
        assert "Connection Refused" in msg
        assert "make docker-up" in msg

    def test_failed_to_connect_format(self):
        exc = Exception("failed to connect to Ollama server")
        msg = format_fatal_error(exc)
        assert "Connection Refused" in msg
        assert "OLLAMA_BASE_URL" in msg

    def test_non_fatal_error_not_detected(self):
        exc = Exception("some random error")
        assert is_fatal_llm_error(exc) is False
