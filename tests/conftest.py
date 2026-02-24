"""Shared test fixtures and configuration."""

from __future__ import annotations

import pytest

from src.config.eval_config import EvalConfig, load_eval_config
from src.evaluator import (
    DimensionScore,
    EvalMode,
    EvalPhase,
    EvaluationResult,
    FullEvaluationReport,
    Grade,
    Improvement,
    OutputDimensionScore,
    OutputEvaluationResult,
    Priority,
    SubCriterionResult,
    TCREIFlags,
)


@pytest.fixture
def eval_config() -> EvalConfig:
    """Default evaluation configuration."""
    return load_eval_config()


@pytest.fixture
def sample_weak_result() -> EvaluationResult:
    """A sample weak evaluation result for testing."""
    return EvaluationResult(
        mode=EvalMode.PROMPT,
        input_text="Write me something about dogs",
        overall_score=12,
        grade=Grade.WEAK,
        dimensions=[
            DimensionScore(name="task", score=18, sub_criteria=[
                SubCriterionResult(name="clear_action_verb", found=True, detail='Action verb "Write" detected'),
                SubCriterionResult(name="specific_deliverable", found=False, detail="No specific deliverable"),
                SubCriterionResult(name="persona_defined", found=False, detail="No persona specified"),
                SubCriterionResult(name="output_format_specified", found=False, detail="No format requested"),
            ]),
            DimensionScore(name="context", score=5, sub_criteria=[]),
            DimensionScore(name="references", score=0, sub_criteria=[]),
            DimensionScore(name="constraints", score=8, sub_criteria=[]),
        ],
        tcrei_flags=TCREIFlags(),
        improvements=[
            Improvement(priority=Priority.CRITICAL, title="Specify the task", suggestion="State what you need"),
        ],
        rewritten_prompt="You're a veterinarian...",
    )


@pytest.fixture
def sample_strong_result() -> EvaluationResult:
    """A sample strong evaluation result for testing."""
    return EvaluationResult(
        mode=EvalMode.PROMPT,
        input_text="You're a vet...",
        overall_score=88,
        grade=Grade.EXCELLENT,
        dimensions=[
            DimensionScore(name="task", score=95, sub_criteria=[]),
            DimensionScore(name="context", score=88, sub_criteria=[]),
            DimensionScore(name="references", score=65, sub_criteria=[]),
            DimensionScore(name="constraints", score=90, sub_criteria=[]),
        ],
        tcrei_flags=TCREIFlags(task=True, context=True, references=True, evaluate=True, iterate=True),
        improvements=[],
        rewritten_prompt=None,
    )


@pytest.fixture
def sample_output_evaluation() -> OutputEvaluationResult:
    """A sample output evaluation result for testing."""
    return OutputEvaluationResult(
        prompt_used="Write a short blog post about dogs",
        llm_output="Dogs are wonderful companions. They bring joy to millions of families worldwide.",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        dimensions=[
            OutputDimensionScore(name="relevance", score=0.85, comment="Output directly addresses dogs", recommendation="No change needed."),
            OutputDimensionScore(name="coherence", score=0.90, comment="Well-structured paragraphs", recommendation="No change needed."),
            OutputDimensionScore(name="completeness", score=0.70, comment="Covers main points", recommendation="Add explicit sub-topic requirements."),
            OutputDimensionScore(name="instruction_following", score=0.80, comment="Blog post format", recommendation="Specify output format constraints."),
            OutputDimensionScore(name="hallucination_risk", score=0.95, comment="No fabricated claims", recommendation="No change needed."),
        ],
        overall_score=0.84,
        grade=Grade.GOOD,
        langsmith_run_id="trace-test-123",
        findings=[
            "Evaluated using LangSmith LLM-as-Judge scoring.",
            "Output is relevant but could be more detailed.",
        ],
    )


@pytest.fixture
def sample_similar_evaluations() -> list[dict]:
    """Sample similar evaluations from embedding search."""
    return [
        {
            "input_text": "Write a blog post about cats for pet owners",
            "rewritten_prompt": "As a pet care expert, write a 500-word blog post...",
            "overall_score": 72,
            "grade": "Good",
            "output_score": 0.78,
            "improvements_summary": "[HIGH] Add specific audience; [MEDIUM] Add format constraints",
            "distance": 0.15,
        },
        {
            "input_text": "Create an article about animal nutrition",
            "rewritten_prompt": None,
            "overall_score": 45,
            "grade": "Needs Work",
            "output_score": 0.55,
            "improvements_summary": "[CRITICAL] Specify deliverable type",
            "distance": 0.28,
        },
    ]


@pytest.fixture
def sample_full_report(
    sample_weak_result: EvaluationResult,
    sample_output_evaluation: OutputEvaluationResult,
) -> FullEvaluationReport:
    """A sample full evaluation report for testing."""
    return FullEvaluationReport(
        phase=EvalPhase.FULL,
        input_text="Write me something about dogs",
        structure_result=sample_weak_result,
        output_result=sample_output_evaluation,
        combined_findings=[
            "[Structure/T.C.R.E.I.] Task — Found: Action verb detected",
            "[Output/LangSmith] Evaluated using LangSmith LLM-as-Judge scoring.",
        ],
        rewritten_prompt="You're a veterinarian...",
    )
