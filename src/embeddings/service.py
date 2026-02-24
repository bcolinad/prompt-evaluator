"""Embedding service — vectorize evaluations and retrieve similar ones."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.embeddings import Embeddings
from sqlalchemy import select

from src.config import get_settings
from src.db.models import ConversationEmbedding

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_embeddings_model: Embeddings | None = None


def _get_embeddings_model() -> Embeddings:
    """Get or create the embeddings model singleton.

    Uses Ollama embeddings (self-hosted, free).
    """
    global _embeddings_model
    if _embeddings_model is None:
        from langchain_ollama import OllamaEmbeddings

        settings = get_settings()

        _embeddings_model = OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )
    return _embeddings_model


_MAX_EMBED_CHARS = 6000  # ~1500 tokens — safe for embedding models


async def generate_embedding(input_text: str) -> list[float]:
    """Generate an embedding vector for the given text.

    Args:
        input_text: Text to vectorize.

    Returns:
        A list of floats representing the embedding vector.
    """
    model = _get_embeddings_model()
    # Truncate long texts to avoid exceeding embedding model context length
    truncated = input_text[:_MAX_EMBED_CHARS] if len(input_text) > _MAX_EMBED_CHARS else input_text
    return await model.aembed_query(truncated)


def _build_summary_text(
    input_text: str,
    rewritten_prompt: str | None,
    overall_score: int,
    grade: str,
    output_score: float | None,
    improvements_summary: str | None,
) -> str:
    """Build a combined text summary for embedding."""
    parts = [f"Prompt: {input_text}"]
    parts.append(f"Score: {overall_score}/100 ({grade})")
    if output_score is not None:
        parts.append(f"Output quality: {int(output_score * 100)}%")
    if improvements_summary:
        parts.append(f"Improvements: {improvements_summary}")
    if rewritten_prompt:
        parts.append(f"Rewritten: {rewritten_prompt[:500]}")
    return "\n".join(parts)


async def store_evaluation_embedding(
    session: AsyncSession,
    user_id: str | None,
    evaluation_id: str | None,
    input_text: str,
    rewritten_prompt: str | None,
    overall_score: int,
    grade: str,
    output_score: float | None,
    improvements_summary: str | None,
    thread_id: str | None = None,
) -> ConversationEmbedding:
    """Vectorize an evaluation and store it in the database.

    Args:
        session: Async database session.
        user_id: Authenticated user identifier.
        evaluation_id: UUID of the evaluation record.
        input_text: The original prompt being evaluated.
        rewritten_prompt: The AI-generated improved version.
        overall_score: Weighted overall score (0-100).
        grade: Grade string (Excellent/Good/Needs Work/Weak).
        output_score: Output quality score (0.0-1.0), if available.
        improvements_summary: Text summary of suggested improvements.
        thread_id: Chainlit thread ID for cleanup on thread deletion.

    Returns:
        The created ConversationEmbedding record.
    """
    summary_text = _build_summary_text(
        input_text, rewritten_prompt, overall_score, grade, output_score, improvements_summary,
    )
    embedding = await generate_embedding(summary_text)

    record = ConversationEmbedding(
        user_id=user_id if user_id and user_id != "anonymous" else None,
        thread_id=thread_id,
        evaluation_id=evaluation_id,
        input_text=input_text,
        rewritten_prompt=rewritten_prompt,
        overall_score=overall_score,
        grade=grade,
        output_score=output_score,
        improvements_summary=improvements_summary,
        embedding=embedding,
    )

    session.add(record)
    await session.flush()
    return record


async def find_similar_evaluations(
    session: AsyncSession,
    query_text: str,
    user_id: str | None = None,
    limit: int | None = None,
    threshold: float | None = None,
) -> list[dict]:
    """Find past evaluations similar to the query text.

    Args:
        session: Async database session.
        query_text: Text to search against.
        user_id: Optional user ID to scope results.
        limit: Max number of results (defaults to settings).
        threshold: Minimum similarity threshold (defaults to settings).

    Returns:
        List of dicts with input_text, rewritten_prompt, overall_score,
        grade, distance, and improvements_summary.
    """
    settings = get_settings()
    limit = limit or settings.max_similar_results or 5
    threshold = threshold or settings.similarity_threshold or 0.7

    query_embedding = await generate_embedding(query_text)

    # Cosine distance: 0 = identical, 2 = opposite. Convert similarity threshold to distance.
    max_distance = 1.0 - threshold
    distance_col = ConversationEmbedding.embedding.cosine_distance(query_embedding).label("distance")

    stmt = (
        select(
            ConversationEmbedding.input_text,
            ConversationEmbedding.rewritten_prompt,
            ConversationEmbedding.overall_score,
            ConversationEmbedding.grade,
            ConversationEmbedding.output_score,
            ConversationEmbedding.improvements_summary,
            distance_col,
        )
        .where(ConversationEmbedding.embedding.cosine_distance(query_embedding) <= max_distance)
        .order_by(ConversationEmbedding.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )

    if user_id and user_id != "anonymous":
        stmt = stmt.where(ConversationEmbedding.user_id == user_id)

    result = await session.execute(stmt)
    rows = result.fetchall()

    return [
        {
            "input_text": row.input_text,
            "rewritten_prompt": row.rewritten_prompt,
            "overall_score": row.overall_score,
            "grade": row.grade,
            "output_score": row.output_score,
            "improvements_summary": row.improvements_summary,
            "distance": row.distance,
        }
        for row in rows
    ]
