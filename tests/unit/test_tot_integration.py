"""Unit tests for Tree-of-Thought integration in the improver node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.nodes.improver import _generate_tot_improvements, generate_improvements
from src.evaluator import EvalMode, TCREIFlags
from src.evaluator.llm_schemas import (
    ImprovementLLMResponse,
    ImprovementsLLMResponse,
    ToTBranchesLLMResponse,
    ToTBranchLLMResponse,
    ToTSelectionLLMResponse,
)
from src.evaluator.strategies import StrategyConfig


def _make_branches_response(n: int = 3) -> ToTBranchesLLMResponse:
    """Create a valid branches response with N branches."""
    branches = []
    for i in range(n):
        branches.append(ToTBranchLLMResponse(
            approach=f"Approach {i + 1}",
            improvements=[
                ImprovementLLMResponse(priority="HIGH", title=f"Improve {i}", suggestion=f"Suggestion {i}"),
            ],
            rewritten_prompt=f"Rewritten prompt branch {i + 1}",
            confidence=0.7 + i * 0.1,
        ))
    return ToTBranchesLLMResponse(branches=branches)


def _make_selection_response(idx: int = 0) -> ToTSelectionLLMResponse:
    return ToTSelectionLLMResponse(
        selected_branch_index=idx,
        synthesized_prompt="Synthesized best prompt",
        rationale="Branch 1 had the best improvements",
    )


def _default_tcrei_flags() -> TCREIFlags:
    """Return default TCREIFlags for test states."""
    return TCREIFlags(task=True, context=False, references=False, evaluate=False, iterate=False)


class TestGenerateToTImprovements:
    @pytest.mark.asyncio
    @patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock)
    async def test_happy_path_branch_and_select(self, mock_invoke):
        branches = _make_branches_response(3)
        selection = _make_selection_response(0)
        mock_invoke.side_effect = [branches, selection]

        result = await _generate_tot_improvements(
            llm=MagicMock(),
            input_text="Write a blog post",
            analysis_summary="Task: 50/100",
            overall_score=50,
            grade="Needs Work",
            output_quality_section="N/A",
            num_branches=3,
        )

        assert result is not None
        assert len(result["improvements"]) == 1
        assert result["rewritten_prompt"] == "Synthesized best prompt"

    @pytest.mark.asyncio
    @patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock)
    async def test_selection_failure_uses_highest_confidence(self, mock_invoke):
        branches = _make_branches_response(3)
        mock_invoke.side_effect = [branches, None]

        result = await _generate_tot_improvements(
            llm=MagicMock(),
            input_text="Write a blog post",
            analysis_summary="Task: 50/100",
            overall_score=50,
            grade="Needs Work",
            output_quality_section="N/A",
            num_branches=3,
        )

        assert result is not None
        # Branch 3 has highest confidence (0.9)
        assert result["rewritten_prompt"] == "Rewritten prompt branch 3"

    @pytest.mark.asyncio
    @patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock)
    async def test_branch_generation_failure_returns_none(self, mock_invoke):
        mock_invoke.return_value = None

        result = await _generate_tot_improvements(
            llm=MagicMock(),
            input_text="Write a blog post",
            analysis_summary="Task: 50/100",
            overall_score=50,
            grade="Needs Work",
            output_quality_section="N/A",
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock)
    async def test_empty_branches_returns_none(self, mock_invoke):
        mock_invoke.return_value = ToTBranchesLLMResponse(branches=[])

        result = await _generate_tot_improvements(
            llm=MagicMock(),
            input_text="Write a blog post",
            analysis_summary="Task: 50/100",
            overall_score=50,
            grade="Needs Work",
            output_quality_section="N/A",
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock)
    async def test_null_branch_index_uses_highest_confidence(self, mock_invoke):
        """When LLM returns null for selected_branch_index, use highest confidence."""
        branches = _make_branches_response(3)
        selection = ToTSelectionLLMResponse(
            selected_branch_index=None,
            synthesized_prompt="Synthesized prompt",
            rationale="Could not decide",
        )
        mock_invoke.side_effect = [branches, selection]

        result = await _generate_tot_improvements(
            llm=MagicMock(),
            input_text="Write a blog post",
            analysis_summary="Task: 50/100",
            overall_score=50,
            grade="Needs Work",
            output_quality_section="N/A",
            num_branches=3,
        )

        assert result is not None
        # Branch 3 has highest confidence (0.9), so its improvements are used
        assert result["improvements"][0].title == "Improve 2"
        # But synthesized prompt from selection is used
        assert result["rewritten_prompt"] == "Synthesized prompt"

    @pytest.mark.asyncio
    @patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock)
    async def test_exception_returns_none(self, mock_invoke):
        mock_invoke.side_effect = RuntimeError("LLM error")

        result = await _generate_tot_improvements(
            llm=MagicMock(),
            input_text="Write a blog post",
            analysis_summary="Task: 50/100",
            overall_score=50,
            grade="Needs Work",
            output_quality_section="N/A",
        )

        assert result is None


class TestGenerateImprovementsWithToT:
    @pytest.mark.asyncio
    @patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value="")
    @patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.improver.get_llm")
    async def test_tot_always_used(self, mock_get_llm, mock_invoke, mock_rag):
        """ToT is always used for improvement generation."""
        branches = _make_branches_response(3)
        selection = _make_selection_response(0)
        mock_invoke.side_effect = [branches, selection]
        mock_get_llm.return_value = MagicMock()

        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "dimension_scores": [],
            "overall_score": 50,
            "grade": "Needs Work",
            "task_type": None,
            "llm_provider": "google",
            "prompt_type": "initial",
            "similar_evaluations": None,
            "tcrei_flags": _default_tcrei_flags(),
            "strategy": StrategyConfig(use_tot=True, tot_num_branches=3),
        }

        result = await generate_improvements(state)
        assert "improvements" in result
        assert result["rewritten_prompt"] == "Synthesized best prompt"
        assert result["tot_branches_data"] is not None

    @pytest.mark.asyncio
    @patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value="")
    @patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.improver.get_llm")
    async def test_tot_used_even_without_explicit_strategy(self, mock_get_llm, mock_invoke, mock_rag):
        """ToT is always used even when no strategy is explicitly set."""
        branches = _make_branches_response(3)
        selection = _make_selection_response(0)
        mock_invoke.side_effect = [branches, selection]
        mock_get_llm.return_value = MagicMock()

        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "dimension_scores": [],
            "overall_score": 50,
            "grade": "Needs Work",
            "task_type": None,
            "llm_provider": "google",
            "prompt_type": "initial",
            "similar_evaluations": None,
            "tcrei_flags": _default_tcrei_flags(),
        }

        result = await generate_improvements(state)
        assert result["rewritten_prompt"] == "Synthesized best prompt"

    @pytest.mark.asyncio
    @patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value="")
    @patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock)
    @patch("src.agent.nodes.improver.get_llm")
    async def test_tot_failure_falls_back_to_standard(self, mock_get_llm, mock_invoke, mock_rag):
        # First call (ToT branch gen) fails, second call (standard) succeeds
        mock_invoke.side_effect = [
            None,  # Branch generation fails -> _generate_tot returns None
            ImprovementsLLMResponse(
                improvements=[ImprovementLLMResponse(priority="MEDIUM", title="Fallback", suggestion="Standard suggestion")],
                rewritten_prompt="Standard rewrite",
            ),
        ]
        mock_get_llm.return_value = MagicMock()

        state = {
            "input_text": "Write a blog post",
            "mode": EvalMode.PROMPT,
            "dimension_scores": [],
            "overall_score": 50,
            "grade": "Needs Work",
            "task_type": None,
            "llm_provider": "google",
            "prompt_type": "initial",
            "similar_evaluations": None,
            "tcrei_flags": _default_tcrei_flags(),
            "strategy": StrategyConfig(use_tot=True),
        }

        result = await generate_improvements(state)
        assert result["rewritten_prompt"] == "Standard rewrite"
        # ToT failed so no branch data
        assert result["tot_branches_data"] is None
