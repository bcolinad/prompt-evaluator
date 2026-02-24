"""Evaluation criteria definitions for each T.C.R.E.I. dimension.

These are used by the LLM-powered scorer to evaluate prompts consistently.
Each criterion includes detection patterns and scoring guidance.
"""

from __future__ import annotations

from src.evaluator.criteria.base import Criterion
from src.evaluator.criteria.coding import (
    CODING_CONSTRAINTS_CRITERIA,
    CODING_CONTEXT_CRITERIA,
    CODING_CRITERIA,
    CODING_REFERENCES_CRITERIA,
    CODING_TASK_CRITERIA,
)
from src.evaluator.criteria.email import (
    EMAIL_CONSTRAINTS_CRITERIA,
    EMAIL_CONTEXT_CRITERIA,
    EMAIL_CRITERIA,
    EMAIL_REFERENCES_CRITERIA,
    EMAIL_TASK_CRITERIA,
)
from src.evaluator.criteria.exam import (
    EXAM_CONSTRAINTS_CRITERIA,
    EXAM_CONTEXT_CRITERIA,
    EXAM_CRITERIA,
    EXAM_REFERENCES_CRITERIA,
    EXAM_TASK_CRITERIA,
)
from src.evaluator.criteria.general import (
    ALL_CRITERIA,
    CONSTRAINTS_CRITERIA,
    CONTEXT_CRITERIA,
    REFERENCES_CRITERIA,
    TASK_CRITERIA,
)
from src.evaluator.criteria.linkedin import (
    LINKEDIN_CONSTRAINTS_CRITERIA,
    LINKEDIN_CONTEXT_CRITERIA,
    LINKEDIN_CRITERIA,
    LINKEDIN_REFERENCES_CRITERIA,
    LINKEDIN_TASK_CRITERIA,
)
from src.evaluator.criteria.summarization import (
    SUMMARIZATION_CONSTRAINTS_CRITERIA,
    SUMMARIZATION_CONTEXT_CRITERIA,
    SUMMARIZATION_CRITERIA,
    SUMMARIZATION_REFERENCES_CRITERIA,
    SUMMARIZATION_TASK_CRITERIA,
)

_CRITERIA_REGISTRY: dict[str, dict[str, list[Criterion]]] = {
    "email_writing": EMAIL_CRITERIA,
    "summarization": SUMMARIZATION_CRITERIA,
    "coding_task": CODING_CRITERIA,
    "exam_interview": EXAM_CRITERIA,
    "linkedin_post": LINKEDIN_CRITERIA,
}


def get_criteria_for_task_type(task_type: str) -> dict[str, list[Criterion]]:
    """Return the criteria dict for the given task type.

    Args:
        task_type: The task type string value.

    Returns:
        The appropriate criteria dictionary.
    """
    return _CRITERIA_REGISTRY.get(task_type, ALL_CRITERIA)


__all__ = [
    "ALL_CRITERIA",
    "CODING_CONSTRAINTS_CRITERIA",
    "CODING_CONTEXT_CRITERIA",
    "CODING_CRITERIA",
    "CODING_REFERENCES_CRITERIA",
    "CODING_TASK_CRITERIA",
    "CONSTRAINTS_CRITERIA",
    "CONTEXT_CRITERIA",
    "EMAIL_CONSTRAINTS_CRITERIA",
    "EMAIL_CONTEXT_CRITERIA",
    "EMAIL_CRITERIA",
    "EMAIL_REFERENCES_CRITERIA",
    "EMAIL_TASK_CRITERIA",
    "EXAM_CONSTRAINTS_CRITERIA",
    "EXAM_CONTEXT_CRITERIA",
    "EXAM_CRITERIA",
    "EXAM_REFERENCES_CRITERIA",
    "EXAM_TASK_CRITERIA",
    "LINKEDIN_CONSTRAINTS_CRITERIA",
    "LINKEDIN_CONTEXT_CRITERIA",
    "LINKEDIN_CRITERIA",
    "LINKEDIN_REFERENCES_CRITERIA",
    "LINKEDIN_TASK_CRITERIA",
    "REFERENCES_CRITERIA",
    "SUMMARIZATION_CONSTRAINTS_CRITERIA",
    "SUMMARIZATION_CONTEXT_CRITERIA",
    "SUMMARIZATION_CRITERIA",
    "SUMMARIZATION_REFERENCES_CRITERIA",
    "SUMMARIZATION_TASK_CRITERIA",
    "TASK_CRITERIA",
    "_CRITERIA_REGISTRY",
    "Criterion",
    "get_criteria_for_task_type",
]
