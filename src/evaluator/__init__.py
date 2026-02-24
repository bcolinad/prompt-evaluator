"""Pydantic models for evaluation inputs, outputs, and scores."""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EvalMode(str, Enum):
    PROMPT = "prompt"
    SYSTEM_PROMPT = "system_prompt"


class EvalPhase(str, Enum):
    STRUCTURE = "structure"
    OUTPUT = "output"
    FULL = "full"


class TaskType(str, Enum):
    GENERAL = "general"
    EMAIL_WRITING = "email_writing"
    SUMMARIZATION = "summarization"
    CODING_TASK = "coding_task"
    EXAM_INTERVIEW = "exam_interview"
    LINKEDIN_POST = "linkedin_post"


class Grade(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    NEEDS_WORK = "Needs Work"
    WEAK = "Weak"


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SubCriterionResult(BaseModel):
    """Result for a single sub-criterion."""

    name: str
    found: bool
    detail: str


class DimensionScore(BaseModel):
    """Score and analysis for a single T.C.R.E.I. dimension."""

    name: str
    score: int = Field(ge=0, le=100)
    sub_criteria: list[SubCriterionResult]

    @property
    def color(self) -> str:
        if self.score >= 70:
            return "#22C55E"  # green
        elif self.score >= 40:
            return "#F59E0B"  # amber
        return "#EF4444"  # red


class Improvement(BaseModel):
    """A single improvement suggestion."""

    priority: Priority
    title: str
    suggestion: str


class TCREIFlags(BaseModel):
    """Which T.C.R.E.I. components are present."""

    task: bool = False
    context: bool = False
    references: bool = False
    evaluate: bool = False
    iterate: bool = False


class EvaluationResult(BaseModel):
    """Complete evaluation output."""

    id: UUID = Field(default_factory=uuid4)
    mode: EvalMode
    input_text: str
    expected_outcome: str | None = None

    # Scores
    overall_score: int = Field(ge=0, le=100)
    grade: Grade
    dimensions: list[DimensionScore]
    tcrei_flags: TCREIFlags

    # Improvements
    improvements: list[Improvement]
    rewritten_prompt: str | None = None

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def grade_color(self) -> str:
        colors = {
            Grade.EXCELLENT: "#22C55E",
            Grade.GOOD: "#3B82F6",
            Grade.NEEDS_WORK: "#F59E0B",
            Grade.WEAK: "#EF4444",
        }
        return colors[self.grade]


class OutputDimensionScore(BaseModel):
    """Score for a single output evaluation dimension."""

    name: str
    score: float = Field(ge=0.0, le=1.0)
    comment: str
    recommendation: str = ""
    evaluation_technique: str = "LangSmith LLM-as-Judge"


class OutputEvaluationResult(BaseModel):
    """Full output evaluation result."""

    prompt_used: str
    llm_output: str
    provider: str
    model: str
    dimensions: list[OutputDimensionScore]
    overall_score: float = Field(ge=0.0, le=1.0)
    grade: Grade
    langsmith_run_id: str | None = None
    findings: list[str] = Field(default_factory=list)


class MetaAssessment(BaseModel):
    """Self-evaluation assessment from the meta-prompting node.

    Each score is a float between 0.0 and 1.0 representing how well
    the evaluation itself performed on each quality dimension.
    """

    accuracy_score: float = Field(default=0.0, ge=0.0, le=1.0)
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    actionability_score: float = Field(default=0.0, ge=0.0, le=1.0)
    faithfulness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ToTBranchAuditEntry(BaseModel):
    """Audit trail entry for a single Tree-of-Thought branch."""

    approach: str
    improvements_count: int
    rewritten_prompt_preview: str  # first 200 chars
    confidence: float = Field(ge=0.0, le=1.0)


class ToTBranchesAuditData(BaseModel):
    """Audit trail for the full ToT exploration."""

    branches: list[ToTBranchAuditEntry]
    selected_branch_index: int
    selection_rationale: str
    synthesized: bool = False


class FullEvaluationReport(BaseModel):
    """Combined report for structure + output evaluation."""

    phase: EvalPhase
    input_text: str
    structure_result: EvaluationResult | None = None
    output_result: OutputEvaluationResult | None = None
    combined_findings: list[str] = Field(default_factory=list)
    rewritten_prompt: str | None = None
    meta_assessment: MetaAssessment | None = None
    strategy_used: str = "enhanced (CoT+ToT+Meta)"
    optimized_output_result: OutputEvaluationResult | None = None
    execution_count: int = 2
    original_outputs: list[str] | None = None
    optimized_outputs: list[str] | None = None
    cot_reasoning_trace: str | None = None
    tot_branches_data: ToTBranchesAuditData | None = None


class EvaluationInput(BaseModel):
    """Input for evaluation — from the user."""

    text: str
    mode: EvalMode = EvalMode.PROMPT
    expected_outcome: str | None = None
    session_id: str | None = None
