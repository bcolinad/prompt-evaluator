"""Centralized LLM factory with three-provider cascade.

Attempts providers in this order:

1. **Google Gemini** via ``ChatGoogleGenerativeAI`` + Vertex AI service account.
2. **Anthropic Claude** via ``ChatAnthropic`` + API key.
3. **Ollama** (self-hosted) via ``ChatOllama`` + local server.

If all three fail, raises with clear setup instructions.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)

# Resolved once at import time — points at src/agent/nodes/google-key.json
_GOOGLE_KEY_PATH = (
    Path(__file__).resolve().parent.parent / "agent" / "nodes" / "google-key.json"
)


def _try_google() -> BaseChatModel | None:
    """Attempt to create a Google Gemini LLM instance.

    Loads the service-account JSON from ``src/agent/nodes/google-key.json``,
    sets ``GOOGLE_APPLICATION_CREDENTIALS``, and returns a
    ``ChatGoogleGenerativeAI`` configured for Vertex AI.

    Returns:
        A ``ChatGoogleGenerativeAI`` instance, or ``None`` on failure.
    """
    from src.config import get_settings

    settings = get_settings()

    if not _GOOGLE_KEY_PATH.exists():
        logger.warning(
            "Google credentials not found at %s — skipping Google provider",
            _GOOGLE_KEY_PATH,
        )
        return None

    try:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(_GOOGLE_KEY_PATH)
        logger.info("Google credentials loaded from: %s", _GOOGLE_KEY_PATH)

        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=settings.google_model,
            project=settings.google_project,
            location=settings.google_location,
            vertexai=True,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_tokens,
            thinking_budget=settings.google_thinking_budget,
            timeout=settings.llm_request_timeout,
        )
        logger.info(
            "LLM provider: Google Gemini (%s) via Vertex AI", settings.google_model
        )
        return llm
    except Exception:
        logger.warning(
            "Google Gemini initialization failed — falling back to Anthropic",
            exc_info=True,
        )
        return None


def _try_anthropic() -> BaseChatModel | None:
    """Attempt to create an Anthropic Claude LLM instance.

    Returns:
        A ``ChatAnthropic`` instance, or ``None`` if the API key is missing.
    """
    from src.config import get_settings

    settings = get_settings()

    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping Anthropic provider")
        return None

    try:
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        logger.info(
            "LLM provider: Anthropic Claude (%s) [fallback]", settings.anthropic_model
        )
        return llm
    except Exception:
        logger.warning("Anthropic initialization failed", exc_info=True)
        return None


def _try_ollama() -> BaseChatModel | None:
    """Attempt to create an Ollama LLM instance.

    Returns:
        A ``ChatOllama`` instance, or ``None`` if the base URL is missing
        or initialization fails.
    """
    from src.config import get_settings

    settings = get_settings()

    if not settings.ollama_base_url:
        logger.warning("OLLAMA_BASE_URL not set — skipping Ollama provider")
        return None

    try:
        from langchain_ollama import ChatOllama

        llm = ChatOllama(
            model=settings.ollama_chat_model,
            base_url=settings.ollama_base_url,
            temperature=settings.llm_temperature,
            num_predict=settings.ollama_num_predict,
            timeout=settings.ollama_request_timeout,
        )
        logger.info(
            "LLM provider: Ollama (%s) at %s [fallback]",
            settings.ollama_chat_model,
            settings.ollama_base_url,
        )
        return llm
    except Exception:
        logger.warning("Ollama initialization failed", exc_info=True)
        return None


def get_llm(provider: str | None = None) -> BaseChatModel:
    """Return a configured LLM instance.

    When *provider* is given, only that specific provider is attempted.
    When ``None``, the cascading fallback order is used:

    1. **Google Gemini** via ``ChatGoogleGenerativeAI`` + Vertex AI.
    2. **Anthropic Claude** via ``ChatAnthropic``.
    3. **Ollama** (self-hosted) via ``ChatOllama``.

    Args:
        provider: Explicit provider key (``"google"``, ``"anthropic"``,
            or ``"ollama"``).
            When ``None``, tries Google → Anthropic → Ollama.

    Returns:
        A configured ``BaseChatModel`` instance.

    Raises:
        RuntimeError: When the requested (or any) provider fails.
    """
    if provider == "google":
        llm = _try_google()
        if llm is not None:
            return llm
        raise RuntimeError(
            "Google Gemini initialization failed.\n\n"
            f"  Place your service-account JSON at: {_GOOGLE_KEY_PATH}\n"
            "  Get credentials: https://console.cloud.google.com/iam-admin/serviceaccounts\n"
            "  Required role: Vertex AI User\n"
        )

    if provider == "anthropic":
        llm = _try_anthropic()
        if llm is not None:
            return llm
        raise RuntimeError(
            "Anthropic Claude initialization failed.\n\n"
            "  Set ANTHROPIC_API_KEY in your .env file\n"
            "  Get an API key: https://console.anthropic.com/\n"
        )

    if provider == "ollama":
        llm = _try_ollama()
        if llm is not None:
            return llm
        raise RuntimeError(
            "Ollama initialization failed.\n\n"
            "  Set OLLAMA_BASE_URL in your .env file (default: http://localhost:11434)\n"
            "  Start Ollama: make docker-up\n"
            "  Pull a model: ollama pull qwen3:4b\n"
        )

    # Auto-detect: try Google first, then Anthropic, then Ollama
    llm = _try_google()
    if llm is not None:
        return llm

    llm = _try_anthropic()
    if llm is not None:
        return llm

    llm = _try_ollama()
    if llm is not None:
        return llm

    raise RuntimeError(
        "No LLM provider available. Configure at least one:\n\n"
        "  OPTION 1 — Google Vertex AI (primary):\n"
        f"    Place your service-account JSON at: {_GOOGLE_KEY_PATH}\n"
        "    Get credentials: https://console.cloud.google.com/iam-admin/serviceaccounts\n"
        "    Required role: Vertex AI User\n\n"
        "  OPTION 2 — Anthropic Claude (fallback):\n"
        "    Set ANTHROPIC_API_KEY in your .env file\n"
        "    Get an API key: https://console.anthropic.com/\n\n"
        "  OPTION 3 — Ollama (self-hosted fallback):\n"
        "    Set OLLAMA_BASE_URL in your .env file (default: http://localhost:11434)\n"
        "    Start Ollama: make docker-up\n"
        "    Pull a model: ollama pull qwen3:4b\n"
    )
