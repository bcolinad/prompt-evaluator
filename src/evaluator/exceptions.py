"""Custom exception hierarchy for the evaluator pipeline."""

from __future__ import annotations


class EvaluatorError(Exception):
    """Base exception for all evaluator errors.

    Args:
        message: Human-readable error description.
        context: Optional dict of extra context for logging/debugging.
    """

    def __init__(self, message: str = "", context: dict | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class LLMError(EvaluatorError):
    """Raised when an LLM invocation fails."""


class AnalysisError(EvaluatorError):
    """Raised when prompt analysis fails."""


class ScoringError(EvaluatorError):
    """Raised when scoring computation fails."""


class ImprovementError(EvaluatorError):
    """Raised when improvement generation fails."""


class OutputEvaluationError(EvaluatorError):
    """Raised when output evaluation (LLM-as-Judge) fails."""


class ReportBuildError(EvaluatorError):
    """Raised when report assembly fails."""


class ConfigurationError(EvaluatorError):
    """Raised when configuration loading or validation fails."""


class OllamaConnectionError(LLMError):
    """Raised when the Ollama server is unreachable."""


class OllamaModelNotFoundError(LLMError):
    """Raised when the requested Ollama model is not pulled."""


class MetaEvaluationError(EvaluatorError):
    """Raised when the meta-evaluation (self-reflection) node fails."""


class StrategyError(EvaluatorError):
    """Raised when strategy resolution or validation fails."""


class APIValidationError(EvaluatorError):
    """Raised when API input validation fails."""


# ── Fatal error detection ────────────────────────────

# Error substrings that indicate the LLM provider is misconfigured or
# the account has a billing/quota problem.  When these are detected the
# evaluation pipeline should stop immediately and surface the error to
# the user instead of silently continuing with fallback zeros.
_FATAL_PATTERNS: list[str] = [
    # Anthropic
    "credit balance is too low",
    "invalid x-api-key",
    "invalid api key",
    "authentication error",
    "permission denied",
    "billing",
    # Google / Vertex AI
    "quota exceeded",
    "resource exhausted",
    "permission_denied",
    "403 forbidden",
    "401 unauthorized",
    "service account",
    "credentials",
    "could not automatically determine credentials",
    # Ollama
    "model not found",
    "connection refused",
    "failed to connect",
    # General
    "rate limit",
    "too many requests",
]


def is_fatal_llm_error(exc: Exception) -> bool:
    """Return True if the exception indicates a fatal provider-level problem.

    Fatal errors are those where retrying or falling back will not help:
    billing issues, invalid API keys, missing credentials, quota exhaustion.

    Args:
        exc: The exception caught from an LLM call.

    Returns:
        True if the evaluation should abort with a user-visible error.
    """
    error_str = str(exc).lower()
    return any(pattern in error_str for pattern in _FATAL_PATTERNS)


def format_fatal_error(exc: Exception) -> str:
    """Format a fatal LLM error into a user-friendly message.

    Args:
        exc: The exception caught from an LLM call.

    Returns:
        A clear, actionable error message for the chat UI.
    """
    error_str = str(exc)
    error_lower = error_str.lower()

    if "credit balance" in error_lower or "billing" in error_lower:
        return (
            f"**LLM Provider Error: Insufficient Credits**\n\n"
            f"The LLM API returned a billing error. Please check your account:\n"
            f"- **Anthropic**: [Plans & Billing](https://console.anthropic.com/settings/billing)\n"
            f"- **Google Cloud**: [Billing](https://console.cloud.google.com/billing)\n\n"
            f"```\n{error_str[:500]}\n```"
        )

    if "api key" in error_lower or "api_key" in error_lower or "authentication" in error_lower:
        return (
            f"**LLM Provider Error: Invalid API Key**\n\n"
            f"The API key is missing or invalid. Check your `.env` file:\n"
            f"- `ANTHROPIC_API_KEY` for Anthropic Claude\n"
            f"- `GOOGLE_APPLICATION_CREDENTIALS` for Google Gemini\n\n"
            f"```\n{error_str[:500]}\n```"
        )

    if "quota" in error_lower or "rate limit" in error_lower or "too many requests" in error_lower:
        return (
            f"**LLM Provider Error: Quota / Rate Limit Exceeded**\n\n"
            f"The API rate limit or quota has been exceeded. "
            f"Wait a moment and try again, or switch providers in Chat Settings.\n\n"
            f"```\n{error_str[:500]}\n```"
        )

    if "model not found" in error_lower:
        return (
            f"**Ollama Error: Model Not Found**\n\n"
            f"The requested model is not available in your Ollama instance. "
            f"Pull it with:\n"
            f"```\nollama pull <model-name>\n```\n"
            f"Or wait for `ollama-pull-qwen3-4b` to finish if using Docker Compose.\n\n"
            f"```\n{error_str[:500]}\n```"
        )

    if "connection refused" in error_lower or "failed to connect" in error_lower:
        return (
            f"**Ollama Error: Connection Refused**\n\n"
            f"Cannot connect to the Ollama server. Make sure it is running:\n"
            f"```\nmake docker-up   # Start Docker services including Ollama\n```\n"
            f"Check that `OLLAMA_BASE_URL` in `.env` is correct "
            f"(default: `http://localhost:11434`).\n\n"
            f"```\n{error_str[:500]}\n```"
        )

    if "credentials" in error_lower or "service account" in error_lower or "permission" in error_lower:
        return (
            f"**LLM Provider Error: Credentials / Permissions**\n\n"
            f"The service account credentials are missing or lack permissions.\n"
            f"- Verify `src/agent/nodes/google-key.json` exists and has the **Vertex AI User** role.\n\n"
            f"```\n{error_str[:500]}\n```"
        )

    return (
        f"**LLM Provider Error**\n\n"
        f"The LLM API call failed with a provider-level error. "
        f"Please check your configuration and try again.\n\n"
        f"```\n{error_str[:500]}\n```"
    )
