"""Unit tests for the meta-evaluator node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.nodes.meta_evaluator import (
    _build_dimension_summary,
    _build_improvements_text,
    meta_evaluate,
)
from src.evaluator import (
    DimensionScore,
    EvalMode,
    Improvement,
    MetaAssessment,
    Priority,
    SubCriterionResult,
)
from src.evaluator.llm_schemas import (
    ImprovementLLMResponse,
    MetaAssessmentLLMResponse,
    MetaEvaluationLLMResponse,
)
from src.evaluator.strategies import StrategyConfig


def _make_meta_response(
    refined: bool = False,
    refined_prompt: str | None = None,
) -> MetaEvaluationLLMResponse:
    """Create a valid meta-evaluation response."""
    resp = MetaEvaluationLLMResponse(
        meta_assessment=MetaAssessmentLLMResponse(
            accuracy_score=0.85,
            completeness_score=0.80,
            actionability_score=0.90,
            faithfulness_score=0.75,
            overall_confidence=0.82,
        ),
        meta_findings=["Evaluation was thorough.", "One minor gap in constraints analysis."],
    )
    if refined:
        resp.refined_improvements = [
            ImprovementLLMResponse(priority="MEDIUM", title="Add length constraint", suggestion="Specify word count"),
        ]
    if refined_prompt:
        resp.refined_rewritten_prompt = refined_prompt
    return resp


class TestBuildDimensionSummary:
    def test_formats_dimensions(self):
        dims = [
            DimensionScore(name="task", score=75, sub_criteria=[
                SubCriterionResult(name="verb", found=True, detail="Found"),
                SubCriterionResult(name="persona", found=False, detail="Missing"),
            ]),
            DimensionScore(name="context", score=40, sub_criteria=[]),
        ]
        result = _build_dimension_summary(dims)
        assert "Task" in result
        assert "75/100" in result
        assert "1/2" in result

    def test_empty_dimensions(self):
        result = _build_dimension_summary([])
        assert "No dimension" in result


class TestBuildImprovementsText:
    def test_formats_improvements(self):
        imps = [
            Improvement(priority=Priority.HIGH, title="Add persona", suggestion="Specify expert role"),
        ]
        result = _build_improvements_text(imps)
        assert "HIGH" in result
        assert "Add persona" in result

    def test_empty_improvements(self):
        result = _build_improvements_text([])
        assert "No improvements" in result


class TestMetaEvaluate:
    @pytest.mark.asyncio
    @patch("src.agent.nodes.meta_evaluator.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.meta_evaluator.get_llm")
    async def test_happy_path(self, mock_get_llm, mock_invoke):
        mock_invoke.return_value = _make_meta_response()
        mock_get_llm.return_value = MagicMock()

        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "overall_score": 50,
            "grade": "Needs Work",
            "dimension_scores": [],
            "improvements": [],
            "rewritten_prompt": "Better blog post",
            "llm_provider": "google",
            "strategy": StrategyConfig(use_meta=True),
        }

        result = await meta_evaluate(state)
        assert result["meta_assessment"] is not None
        assert isinstance(result["meta_assessment"], MetaAssessment)
        assert result["meta_assessment"].accuracy_score == 0.85
        assert len(result["meta_findings"]) == 2
        assert "improvements" not in result  # No refined improvements in this response

    @pytest.mark.asyncio
    @patch("src.agent.nodes.meta_evaluator.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.meta_evaluator.get_llm")
    async def test_with_refined_improvements(self, mock_get_llm, mock_invoke):
        mock_invoke.return_value = _make_meta_response(refined=True)
        mock_get_llm.return_value = MagicMock()

        existing_imp = Improvement(priority=Priority.HIGH, title="Original", suggestion="Original suggestion")
        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "overall_score": 50,
            "grade": "Needs Work",
            "dimension_scores": [],
            "improvements": [existing_imp],
            "rewritten_prompt": "Better blog post",
            "llm_provider": "google",
            "strategy": StrategyConfig(use_meta=True),
        }

        result = await meta_evaluate(state)
        assert "improvements" in result
        assert len(result["improvements"]) == 2  # original + refined
        assert result["improvements"][1].title.startswith("[Meta]")

    @pytest.mark.asyncio
    @patch("src.agent.nodes.meta_evaluator.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.meta_evaluator.get_llm")
    async def test_with_refined_rewritten_prompt(self, mock_get_llm, mock_invoke):
        mock_invoke.return_value = _make_meta_response(refined_prompt="Even better prompt")
        mock_get_llm.return_value = MagicMock()

        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "overall_score": 50,
            "grade": "Needs Work",
            "dimension_scores": [],
            "improvements": [],
            "rewritten_prompt": "Better blog post",
            "llm_provider": "google",
            "strategy": StrategyConfig(use_meta=True),
        }

        result = await meta_evaluate(state)
        assert result["rewritten_prompt"] == "Even better prompt"

    @pytest.mark.asyncio
    @patch("src.agent.nodes.meta_evaluator.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.meta_evaluator.get_llm")
    async def test_no_result_graceful_fallback(self, mock_get_llm, mock_invoke):
        mock_invoke.return_value = None
        mock_get_llm.return_value = MagicMock()

        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "overall_score": 50,
            "grade": "Needs Work",
            "dimension_scores": [],
            "improvements": [],
            "rewritten_prompt": "Better blog post",
            "llm_provider": "google",
            "strategy": StrategyConfig(use_meta=True),
        }

        result = await meta_evaluate(state)
        assert result["meta_assessment"] is None
        assert "Meta-evaluation could not produce" in result["meta_findings"][0]

    @pytest.mark.asyncio
    @patch("src.agent.nodes.meta_evaluator.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.meta_evaluator.get_llm")
    async def test_llm_failure_graceful_fallback(self, mock_get_llm, mock_invoke):
        mock_invoke.side_effect = RuntimeError("LLM error")
        mock_get_llm.return_value = MagicMock()

        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "overall_score": 50,
            "grade": "Needs Work",
            "dimension_scores": [],
            "improvements": [],
            "rewritten_prompt": "Better blog post",
            "llm_provider": "google",
            "strategy": StrategyConfig(use_meta=True),
        }

        result = await meta_evaluate(state)
        assert result["meta_assessment"] is None
        assert "Meta-evaluation failed" in result["meta_findings"][0]

    @pytest.mark.asyncio
    @patch("src.agent.nodes.meta_evaluator.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.meta_evaluator.get_llm")
    async def test_fatal_error_returns_error_message(self, mock_get_llm, mock_invoke):
        mock_invoke.side_effect = RuntimeError("credit balance is too low")
        mock_get_llm.return_value = MagicMock()

        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "overall_score": 50,
            "grade": "Needs Work",
            "dimension_scores": [],
            "improvements": [],
            "rewritten_prompt": "Better blog post",
            "llm_provider": "google",
            "strategy": StrategyConfig(use_meta=True),
        }

        result = await meta_evaluate(state)
        assert "error_message" in result
        assert "Insufficient Credits" in result["error_message"]
