"""LangSmith integration utilities for output evaluation scoring."""

from __future__ import annotations

import logging

from langsmith import Client

logger = logging.getLogger(__name__)


def get_langsmith_client() -> Client | None:
    """Return a LangSmith client if tracing is enabled and configured, else None."""
    from src.config import get_settings

    settings = get_settings()
    if not settings.langchain_tracing_v2:
        return None

    if not settings.langchain_api_key:
        logger.warning("LangSmith tracing enabled but missing LANGCHAIN_API_KEY — skipping.")
        return None

    return Client()


def score_run(run_id: str, key: str, score: float, comment: str | None = None) -> None:
    """Attach a numeric score as feedback to a LangSmith run.

    Args:
        run_id: The LangSmith run ID to score.
        key: Feedback key (e.g. "relevance", "coherence").
        score: Numeric score (0.0 - 1.0).
        comment: Optional human-readable comment.
    """
    client = get_langsmith_client()
    if client is None:
        return

    try:
        client.create_feedback(
            run_id=run_id,
            key=key,
            score=score,
            comment=comment,
        )
    except Exception:
        logger.exception("Failed to score run %s", run_id)
