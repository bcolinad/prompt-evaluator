"""Pydantic schemas for structured LLM responses.

These schemas define the exact JSON structure expected from each LLM call.
They are used with ``with_structured_output()`` for reliable parsing, with
a ``json.loads()`` + ``model_validate()`` fallback path.

These are separate from domain models in ``src/evaluator/__init__.py``
because LLM response shapes may differ from the domain objects (e.g.
different field names, nested differently, or including raw scores
before post-processing).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Analysis Schemas ─────────────────────────────────

class SubCriterionLLMResponse(BaseModel):
    """A single sub-criterion result from the LLM."""

    name: str = ""
    found: bool = False
    detail: str = ""


class DimensionLLMResponse(BaseModel):
    """A single dimension analysis from the LLM."""

    score: int = Field(default=0, ge=0, le=100)
    sub_criteria: list[SubCriterionLLMResponse] = Field(default_factory=list)


class TCREIFlagsLLMResponse(BaseModel):
    """T.C.R.E.I. presence flags from the LLM."""

    task: bool = False
    context: bool = False
    references: bool = False
    evaluate: bool = False
    iterate: bool = False


class AnalysisLLMResponse(BaseModel):
    """Full analysis response from the LLM."""

    dimensions: dict[str, DimensionLLMResponse] = Field(default_factory=dict)
    tcrei_flags: TCREIFlagsLLMResponse = Field(default_factory=TCREIFlagsLLMResponse)


# ── Improvement Schemas ──────────────────────────────

class ImprovementLLMResponse(BaseModel):
    """A single improvement suggestion from the LLM."""

    priority: str = "MEDIUM"
    title: str = ""
    suggestion: str = ""


class ImprovementsLLMResponse(BaseModel):
    """Full improvements response from the LLM."""

    improvements: list[ImprovementLLMResponse] = Field(default_factory=list)
    rewritten_prompt: str | None = None


# ── Output Evaluation Schemas ────────────────────────

class OutputDimensionLLMResponse(BaseModel):
    """A single output evaluation dimension from the LLM."""

    name: str = "unknown"
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    comment: str = ""
    recommendation: str = ""


class OutputEvaluationLLMResponse(BaseModel):
    """Full output evaluation response from the LLM."""

    dimensions: list[OutputDimensionLLMResponse] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    findings: list[str] = Field(default_factory=list)


# ── Follow-up Schemas ────────────────────────────────

class FollowupLLMResponse(BaseModel):
    """Follow-up conversation response from the LLM."""

    intent: str = "explain"
    response: str = ""
    new_prompt: str | None = None
    new_rewrite: str | None = None
    new_mode: str | None = None


# ── Tree-of-Thought Schemas ─────────────────────────

class ToTBranchLLMResponse(BaseModel):
    """A single Tree-of-Thought improvement branch from the LLM."""

    approach: str = ""
    improvements: list[ImprovementLLMResponse] = Field(default_factory=list)
    rewritten_prompt: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ToTBranchesLLMResponse(BaseModel):
    """All ToT branches generated in the divergent phase."""

    branches: list[ToTBranchLLMResponse] = Field(default_factory=list)


class ToTSelectionLLMResponse(BaseModel):
    """ToT convergent phase — select or synthesize the best branch."""

    selected_branch_index: int | None = 0
    synthesized_prompt: str = ""
    rationale: str = ""


# ── Meta-Evaluation Schemas ─────────────────────────

class MetaAssessmentLLMResponse(BaseModel):
    """Self-evaluation quality scores from the meta-prompting LLM."""

    accuracy_score: float = Field(default=0.5, ge=0.0, le=1.0)
    completeness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    actionability_score: float = Field(default=0.5, ge=0.0, le=1.0)
    faithfulness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class MetaEvaluationLLMResponse(BaseModel):
    """Full meta-evaluation response from the LLM."""

    meta_assessment: MetaAssessmentLLMResponse = Field(default_factory=MetaAssessmentLLMResponse)
    refined_improvements: list[ImprovementLLMResponse] = Field(default_factory=list)
    refined_rewritten_prompt: str | None = None
    meta_findings: list[str] = Field(default_factory=list)
