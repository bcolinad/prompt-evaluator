"""Scorer node — computes overall score and grade from dimension scores."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage

from src.agent.state import AgentState
from src.config.eval_config import load_eval_config
from src.evaluator.exceptions import ScoringError

logger = logging.getLogger(__name__)


async def score_prompt(state: AgentState) -> dict:
    """Compute the overall weighted score and assign a grade.

    Uses the evaluation config weights to combine dimension scores
    into a single overall score, then maps to a grade.

    Args:
        state: Current agent state containing dimension_scores.

    Returns:
        State update dict with overall_score, grade, and messages.
        On error, falls back to score=0, grade="Weak".
    """
    try:
        task_type = getattr(state.get("task_type"), "value", "general")
        config = load_eval_config(task_type=task_type)
        dimensions = state.get("dimension_scores", [])

        if not dimensions:
            return {
                "overall_score": 0,
                "grade": "Weak",
                "current_step": "scoring_complete",
            }

        # Build dimension name -> score mapping
        dimension_scores = {d.name: d.score for d in dimensions}

        # Compute weighted overall
        overall = config.compute_overall(dimension_scores)
        grade = config.get_grade(overall)

        # Format score summary for thinking display
        score_parts = " | ".join(f"{d.name.title()}: {d.score}" for d in dimensions)
        summary = f"🎯 Scores: {score_parts} → **Overall: {overall}/100 ({grade})**"

        return {
            "overall_score": overall,
            "grade": grade,
            "current_step": "scoring_complete",
            "messages": [AIMessage(content=summary)],
        }

    except Exception as exc:
        logger.exception("score_prompt failed: %s", exc)
        domain_err = ScoringError(
            f"Scoring computation failed: {exc}",
            context={"dimension_count": len(state.get("dimension_scores", [])), "original_error": str(exc)},
        )
        logger.error("Domain error: %s context=%s", domain_err, domain_err.context)
        return {
            "overall_score": 0,
            "grade": "Weak",
            "current_step": "scoring_complete",
            "messages": [
                AIMessage(content=f"Scoring failed: {type(exc).__name__}: {exc}. Defaulting to 0/Weak.")
            ],
        }
