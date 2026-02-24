"""Load and validate evaluation configuration from YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SubCriteria(BaseModel):
    """A single sub-criterion within a dimension."""

    name: str
    description: str = ""


class DimensionConfig(BaseModel):
    """Configuration for a single evaluation dimension."""

    weight: float = Field(ge=0.0, le=1.0)
    sub_criteria: list[str]


class GradingScale(BaseModel):
    """Score thresholds for each grade."""

    excellent: int = 85
    good: int = 65
    needs_work: int = 40
    weak: int = 0


class EvalConfig(BaseModel):
    """Full evaluation configuration."""

    dimensions: dict[str, DimensionConfig]
    grading_scale: GradingScale = GradingScale()

    def get_grade(self, score: int) -> str:
        """Determine grade from overall score."""
        if score >= self.grading_scale.excellent:
            return "Excellent"
        elif score >= self.grading_scale.good:
            return "Good"
        elif score >= self.grading_scale.needs_work:
            return "Needs Work"
        return "Weak"

    def compute_overall(self, dimension_scores: dict[str, int]) -> int:
        """Compute weighted overall score from dimension scores."""
        total = 0.0
        for name, config in self.dimensions.items():
            score = dimension_scores.get(name, 0)
            total += score * config.weight
        return round(total)


def load_eval_config(path: Path | None = None, task_type: str = "general") -> EvalConfig:
    """Load evaluation config from YAML file. Falls back to default.

    Args:
        path: Optional explicit path to a YAML config file.
        task_type: The task type ("general", "email_writing", or "summarization") to select the config.
    """
    if path is None:
        if task_type == "email_writing":
            path = Path(__file__).parent / "defaults" / "email_writing_eval_config.yaml"
        elif task_type == "summarization":
            path = Path(__file__).parent / "defaults" / "summarization_eval_config.yaml"
        elif task_type == "coding_task":
            path = Path(__file__).parent / "defaults" / "coding_task_eval_config.yaml"
        elif task_type == "exam_interview":
            path = Path(__file__).parent / "defaults" / "exam_interview_eval_config.yaml"
        elif task_type == "linkedin_post":
            path = Path(__file__).parent / "defaults" / "linkedin_post_eval_config.yaml"
        else:
            path = Path(__file__).parent / "defaults" / "eval_config.yaml"

    if not path.exists():
        return _default_config()

    with open(path) as f:
        data: dict[str, Any] = yaml.safe_load(f)

    return EvalConfig(**data.get("evaluation", data))


def _default_config() -> EvalConfig:
    """Return hardcoded default configuration."""
    return EvalConfig(
        dimensions={
            "task": DimensionConfig(weight=0.30, sub_criteria=["clear_action_verb", "specific_deliverable", "persona_defined", "output_format_specified"]),
            "context": DimensionConfig(weight=0.25, sub_criteria=["background_provided", "audience_defined", "goals_stated", "domain_specificity"]),
            "references": DimensionConfig(weight=0.20, sub_criteria=["examples_included", "structured_references", "reference_labeling"]),
            "constraints": DimensionConfig(weight=0.25, sub_criteria=["scope_boundaries", "format_constraints", "length_limits", "exclusions_defined"]),
        },
    )
