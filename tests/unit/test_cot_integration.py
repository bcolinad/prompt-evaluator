"""Unit tests for Chain-of-Thought integration in the analyzer node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.nodes.analyzer import _analyze_single, analyze_prompt
from src.evaluator import EvalMode, TaskType
from src.evaluator.llm_schemas import (
    AnalysisLLMResponse,
    DimensionLLMResponse,
    SubCriterionLLMResponse,
    TCREIFlagsLLMResponse,
)
from src.evaluator.strategies import StrategyConfig


def _make_analysis_response() -> AnalysisLLMResponse:
    """Create a minimal valid analysis response for mocking."""
    return AnalysisLLMResponse(
        dimensions={
            "task": DimensionLLMResponse(score=50, sub_criteria=[
                SubCriterionLLMResponse(name="action_verb", found=True, detail="Found verb"),
            ]),
            "context": DimensionLLMResponse(score=30, sub_criteria=[]),
            "references": DimensionLLMResponse(score=10, sub_criteria=[]),
            "constraints": DimensionLLMResponse(score=20, sub_criteria=[]),
        },
        tcrei_flags=TCREIFlagsLLMResponse(task=True),
    )


class TestCoTInAnalyzeSingle:
    @pytest.mark.asyncio
    @patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.analyzer.get_llm")
    async def test_cot_preamble_always_prepended(self, mock_get_llm, mock_invoke):
        """CoT preamble is always prepended since CoT is always active."""
        mock_invoke.return_value = _make_analysis_response()
        mock_get_llm.return_value = MagicMock()

        original_prompt = "You are an evaluator. {criteria} {rag_context}"
        await _analyze_single(
            input_text="Test prompt",
            criteria_desc="criteria",
            rag_section="",
            analysis_prompt=original_prompt,
        )

        # The prompt template should have been called with CoT preamble prepended
        call_args = mock_invoke.call_args
        prompt_template = call_args[0][1]  # second positional arg is the prompt
        # Extract system message content from the ChatPromptTemplate
        messages = prompt_template.format_messages(input_text="Test prompt")
        system_content = messages[0].content
        assert "STEP 1" in system_content
        assert "Chain-of-Thought" in system_content

    @pytest.mark.asyncio
    @patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.analyzer.get_llm")
    async def test_output_format_unchanged_with_cot(self, mock_get_llm, mock_invoke):
        """CoT changes reasoning, not output schema."""
        mock_invoke.return_value = _make_analysis_response()
        mock_get_llm.return_value = MagicMock()

        original_prompt = "You are an evaluator. {criteria} {rag_context}"
        result = await _analyze_single(
            input_text="Test prompt",
            criteria_desc="criteria",
            rag_section="",
            analysis_prompt=original_prompt,
        )

        assert "dimensions" in result
        assert "tcrei_flags" in result
        assert len(result["dimensions"]) == 4


class TestCoTInAnalyzePrompt:
    @pytest.mark.asyncio
    @patch("src.agent.nodes.analyzer._retrieve_similar_evaluations", new_callable=AsyncMock, return_value=[])
    @patch("src.agent.nodes.analyzer.retrieve_context", new_callable=AsyncMock, return_value="")
    @patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.analyzer.get_llm")
    async def test_cot_always_applied_with_strategy(
        self, mock_get_llm, mock_invoke, mock_rag, mock_similar
    ):
        mock_invoke.return_value = _make_analysis_response()
        mock_get_llm.return_value = MagicMock()

        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "task_type": TaskType.GENERAL,
            "llm_provider": "google",
            "user_id": "test",
            "strategy": StrategyConfig(use_cot=True),
        }

        result = await analyze_prompt(state)
        assert result["dimension_scores"] is not None

        # Verify the prompt included CoT preamble
        call_args = mock_invoke.call_args
        prompt_template = call_args[0][1]
        messages = prompt_template.format_messages(input_text="Test")
        system_content = messages[0].content
        assert "STEP 1" in system_content

    @pytest.mark.asyncio
    @patch("src.agent.nodes.analyzer._retrieve_similar_evaluations", new_callable=AsyncMock, return_value=[])
    @patch("src.agent.nodes.analyzer.retrieve_context", new_callable=AsyncMock, return_value="")
    @patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.analyzer.get_llm")
    async def test_cot_always_applied_without_strategy(
        self, mock_get_llm, mock_invoke, mock_rag, mock_similar
    ):
        """CoT is always applied even when no strategy is provided."""
        mock_invoke.return_value = _make_analysis_response()
        mock_get_llm.return_value = MagicMock()

        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "task_type": TaskType.GENERAL,
            "llm_provider": "google",
            "user_id": "test",
        }

        result = await analyze_prompt(state)
        assert result["dimension_scores"] is not None

        call_args = mock_invoke.call_args
        prompt_template = call_args[0][1]
        messages = prompt_template.format_messages(input_text="Test")
        system_content = messages[0].content
        # CoT is always on, so preamble should be present
        assert "Chain-of-Thought" in system_content

    @pytest.mark.asyncio
    @patch("src.agent.nodes.analyzer._retrieve_similar_evaluations", new_callable=AsyncMock, return_value=[])
    @patch("src.agent.nodes.analyzer.retrieve_context", new_callable=AsyncMock, return_value="")
    @patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.analyzer.get_llm")
    async def test_cot_reasoning_trace_returned(
        self, mock_get_llm, mock_invoke, mock_rag, mock_similar
    ):
        """analyze_prompt returns a cot_reasoning_trace in its state update."""
        mock_invoke.return_value = _make_analysis_response()
        mock_get_llm.return_value = MagicMock()

        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "task_type": TaskType.GENERAL,
            "llm_provider": "google",
            "user_id": "test",
            "strategy": StrategyConfig(use_cot=True),
        }

        result = await analyze_prompt(state)
        assert "cot_reasoning_trace" in result
        assert result["cot_reasoning_trace"] is not None
