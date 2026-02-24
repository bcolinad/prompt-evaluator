"""Centralized task-type prompt registry — eliminates elif chains in agent nodes."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.prompts import (
    ANALYSIS_SYSTEM_PROMPT,
    CODING_ANALYSIS_SYSTEM_PROMPT,
    CODING_IMPROVEMENT_GUIDANCE,
    CODING_OUTPUT_EVALUATION_SYSTEM_PROMPT,
    EMAIL_ANALYSIS_SYSTEM_PROMPT,
    EMAIL_IMPROVEMENT_GUIDANCE,
    EMAIL_OUTPUT_EVALUATION_SYSTEM_PROMPT,
    EXAM_ANALYSIS_SYSTEM_PROMPT,
    EXAM_IMPROVEMENT_GUIDANCE,
    EXAM_OUTPUT_EVALUATION_SYSTEM_PROMPT,
    LINKEDIN_ANALYSIS_SYSTEM_PROMPT,
    LINKEDIN_IMPROVEMENT_GUIDANCE,
    LINKEDIN_OUTPUT_EVALUATION_SYSTEM_PROMPT,
    OUTPUT_EVALUATION_SYSTEM_PROMPT,
    SUMMARIZATION_ANALYSIS_SYSTEM_PROMPT,
    SUMMARIZATION_IMPROVEMENT_GUIDANCE,
    SUMMARIZATION_OUTPUT_EVALUATION_SYSTEM_PROMPT,
)


@dataclass(frozen=True)
class TaskTypePrompts:
    """Prompt templates and fallback data for a single task type."""

    analysis: str
    output_evaluation: str
    improvement_guidance: str
    fallback_dimensions: tuple[tuple[str, str], ...] = field(default_factory=tuple)


_REGISTRY: dict[str, TaskTypePrompts] = {
    "general": TaskTypePrompts(
        analysis=ANALYSIS_SYSTEM_PROMPT,
        output_evaluation=OUTPUT_EVALUATION_SYSTEM_PROMPT,
        improvement_guidance="",
        fallback_dimensions=(
            ("relevance", "Could not evaluate relevance."),
            ("coherence", "Could not evaluate coherence."),
            ("completeness", "Could not evaluate completeness."),
            ("instruction_following", "Could not evaluate instruction following."),
            ("hallucination_risk", "Could not evaluate hallucination risk."),
        ),
    ),
    "email_writing": TaskTypePrompts(
        analysis=EMAIL_ANALYSIS_SYSTEM_PROMPT,
        output_evaluation=EMAIL_OUTPUT_EVALUATION_SYSTEM_PROMPT,
        improvement_guidance=EMAIL_IMPROVEMENT_GUIDANCE,
        fallback_dimensions=(
            ("tone_appropriateness", "Could not evaluate tone appropriateness."),
            ("professional_email_structure", "Could not evaluate email structure."),
            ("audience_fit", "Could not evaluate audience fit."),
            ("purpose_achievement", "Could not evaluate purpose achievement."),
            ("conciseness_clarity", "Could not evaluate conciseness and clarity."),
        ),
    ),
    "summarization": TaskTypePrompts(
        analysis=SUMMARIZATION_ANALYSIS_SYSTEM_PROMPT,
        output_evaluation=SUMMARIZATION_OUTPUT_EVALUATION_SYSTEM_PROMPT,
        improvement_guidance=SUMMARIZATION_IMPROVEMENT_GUIDANCE,
        fallback_dimensions=(
            ("information_accuracy", "Could not evaluate information accuracy."),
            ("logical_structure", "Could not evaluate logical structure."),
            ("key_information_coverage", "Could not evaluate key information coverage."),
            ("source_fidelity", "Could not evaluate source fidelity."),
            ("conciseness_precision", "Could not evaluate conciseness and precision."),
        ),
    ),
    "coding_task": TaskTypePrompts(
        analysis=CODING_ANALYSIS_SYSTEM_PROMPT,
        output_evaluation=CODING_OUTPUT_EVALUATION_SYSTEM_PROMPT,
        improvement_guidance=CODING_IMPROVEMENT_GUIDANCE,
        fallback_dimensions=(
            ("code_correctness", "Could not evaluate code correctness."),
            ("code_quality", "Could not evaluate code quality."),
            ("requirements_coverage", "Could not evaluate requirements coverage."),
            ("error_handling_security", "Could not evaluate error handling and security."),
            ("maintainability", "Could not evaluate maintainability."),
        ),
    ),
    "exam_interview": TaskTypePrompts(
        analysis=EXAM_ANALYSIS_SYSTEM_PROMPT,
        output_evaluation=EXAM_OUTPUT_EVALUATION_SYSTEM_PROMPT,
        improvement_guidance=EXAM_IMPROVEMENT_GUIDANCE,
        fallback_dimensions=(
            ("question_quality", "Could not evaluate question quality."),
            ("assessment_coverage", "Could not evaluate assessment coverage."),
            ("difficulty_calibration", "Could not evaluate difficulty calibration."),
            ("rubric_completeness", "Could not evaluate rubric completeness."),
            ("fairness_objectivity", "Could not evaluate fairness and objectivity."),
        ),
    ),
    "linkedin_post": TaskTypePrompts(
        analysis=LINKEDIN_ANALYSIS_SYSTEM_PROMPT,
        output_evaluation=LINKEDIN_OUTPUT_EVALUATION_SYSTEM_PROMPT,
        improvement_guidance=LINKEDIN_IMPROVEMENT_GUIDANCE,
        fallback_dimensions=(
            ("professional_tone_authenticity", "Could not evaluate professional tone and authenticity."),
            ("hook_scroll_stopping_power", "Could not evaluate hook and scroll-stopping power."),
            ("audience_engagement_potential", "Could not evaluate audience engagement potential."),
            ("value_delivery_expertise", "Could not evaluate value delivery and expertise showcase."),
            ("linkedin_platform_optimization", "Could not evaluate LinkedIn platform optimization."),
        ),
    ),
}


def get_prompts_for_task_type(task_type: str) -> TaskTypePrompts:
    """Look up prompt templates for a task type.

    Args:
        task_type: Task type string (e.g. ``"general"``, ``"email_writing"``).

    Returns:
        The matching ``TaskTypePrompts``, falling back to ``"general"``.
    """
    return _REGISTRY.get(task_type, _REGISTRY["general"])
