"""Unit tests for the evaluate_optimized_output node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.nodes.output_evaluator import evaluate_optimized_output
from src.evaluator import TaskType


class TestEvaluateOptimizedOutput:
    @pytest.mark.asyncio
    async def test_skips_when_no_optimized_output(self):
        state = {
            "input_text": "test",
            "session_id": "test",
        }
        result = await evaluate_optimized_output(state)

        assert result["optimized_output_evaluation"] is None
        assert result["current_step"] == "optimized_output_evaluated"

    @pytest.mark.asyncio
    async def test_skips_when_no_rewritten_prompt(self):
        state = {
            "input_text": "test",
            "optimized_output_summary": "Some output",
            "session_id": "test",
        }
        result = await evaluate_optimized_output(state)

        assert result["optimized_output_evaluation"] is None

    @pytest.mark.asyncio
    async def test_evaluates_when_both_present(self):
        from src.evaluator.llm_schemas import OutputEvaluationLLMResponse

        mock_parsed = MagicMock(spec=OutputEvaluationLLMResponse)
        mock_dim = MagicMock(score=0.85, comment="Good relevance", recommendation="Keep it up")
        mock_dim.name = "relevance"
        mock_parsed.dimensions = [mock_dim]
        mock_parsed.overall_score = 0.85
        mock_parsed.findings = ["Good quality"]

        mock_llm = AsyncMock()

        with (
            patch("src.agent.nodes.output_evaluator.get_llm", return_value=mock_llm),
            patch("src.agent.nodes.output_evaluator.invoke_structured", return_value=mock_parsed),
            patch("src.agent.nodes.output_evaluator.get_settings") as mock_settings,
            patch("src.agent.nodes.output_evaluator.score_run"),
            patch("src.agent.nodes.output_evaluator.collect_runs") as mock_collect,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.llm_provider = MagicMock(value="google")
            mock_settings_obj.google_model = "gemini-2.5-flash"
            mock_settings.return_value = mock_settings_obj

            mock_cb = MagicMock()
            mock_cb.traced_runs = []
            mock_collect.return_value.__enter__ = MagicMock(return_value=mock_cb)
            mock_collect.return_value.__exit__ = MagicMock(return_value=False)

            state = {
                "input_text": "test",
                "rewritten_prompt": "Optimized test prompt",
                "optimized_output_summary": "Generated optimized output",
                "task_type": TaskType.GENERAL,
                "session_id": "test",
            }
            result = await evaluate_optimized_output(state)

        assert result["optimized_output_evaluation"] is not None
        assert result["current_step"] == "optimized_output_evaluated"

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        mock_llm = AsyncMock()

        with (
            patch("src.agent.nodes.output_evaluator.get_llm", return_value=mock_llm),
            patch("src.agent.nodes.output_evaluator.invoke_structured", side_effect=RuntimeError("API error")),
            patch("src.agent.nodes.output_evaluator.collect_runs") as mock_collect,
        ):
            mock_cb = MagicMock()
            mock_cb.traced_runs = []
            mock_collect.return_value.__enter__ = MagicMock(return_value=mock_cb)
            mock_collect.return_value.__exit__ = MagicMock(return_value=False)

            state = {
                "input_text": "test",
                "rewritten_prompt": "Optimized test prompt",
                "optimized_output_summary": "Generated output",
                "task_type": TaskType.GENERAL,
                "session_id": "test",
            }
            result = await evaluate_optimized_output(state)

        assert result["optimized_output_evaluation"] is None
        assert result["current_step"] == "optimized_output_evaluated"
