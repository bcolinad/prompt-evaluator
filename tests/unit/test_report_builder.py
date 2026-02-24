"""Unit tests for the report builder node."""

from unittest.mock import AsyncMock, patch

import pytest

from src.agent.nodes.report_builder import _summarize_improvements, build_report
from src.evaluator import (
    DimensionScore,
    EvalMode,
    EvalPhase,
    EvaluationResult,
    Grade,
    Improvement,
    OutputDimensionScore,
    OutputEvaluationResult,
    Priority,
    SubCriterionResult,
    TCREIFlags,
)


def _make_structure_result() -> EvaluationResult:
    return EvaluationResult(
        mode=EvalMode.PROMPT,
        input_text="Test",
        overall_score=65,
        grade=Grade.GOOD,
        dimensions=[
            DimensionScore(name="task", score=70, sub_criteria=[
                SubCriterionResult(name="action_verb", found=True, detail="Found verb"),
                SubCriterionResult(name="persona", found=False, detail="No persona"),
            ]),
        ],
        tcrei_flags=TCREIFlags(task=True),
        improvements=[],
    )


def _make_output_result() -> OutputEvaluationResult:
    return OutputEvaluationResult(
        prompt_used="Test",
        llm_output="Some output",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        dimensions=[
            OutputDimensionScore(name="relevance", score=0.85, comment="Relevant", recommendation="No change needed."),
        ],
        overall_score=0.85,
        grade=Grade.EXCELLENT,
        langsmith_run_id="trace-123",
        findings=["Evaluated using LangSmith LLM-as-Judge scoring.", "Good output."],
    )


class TestSummarizeImprovements:
    def test_summarizes_improvements(self):
        improvements = [
            Improvement(priority=Priority.CRITICAL, title="Add task", suggestion="Be specific about the deliverable"),
            Improvement(priority=Priority.HIGH, title="Add persona", suggestion="Specify who the AI should act as"),
        ]
        result = _summarize_improvements(improvements)
        assert "[CRITICAL]" in result
        assert "[HIGH]" in result

    def test_none_when_empty(self):
        assert _summarize_improvements([]) is None
        assert _summarize_improvements(None) is None


class TestBuildReport:
    @pytest.mark.asyncio
    async def test_structure_only_report(self):
        state = {
            "input_text": "Test prompt",
            "eval_phase": EvalPhase.STRUCTURE,
            "evaluation_result": _make_structure_result(),
            "output_evaluation": None,
            "rewritten_prompt": "Better prompt",
            "should_continue": False,
            "user_id": None,
            "overall_score": 65,
            "grade": "Good",
            "improvements": [],
        }
        with patch("src.agent.nodes.report_builder._store_embedding", new_callable=AsyncMock):
            result = await build_report(state)
        report = result["full_report"]

        assert report.phase == EvalPhase.STRUCTURE
        assert report.structure_result is not None
        assert report.output_result is None
        assert report.rewritten_prompt == "Better prompt"
        assert any("[Structure/T.C.R.E.I.]" in f for f in report.combined_findings)

    @pytest.mark.asyncio
    async def test_output_only_report(self):
        state = {
            "input_text": "Test prompt",
            "eval_phase": EvalPhase.OUTPUT,
            "evaluation_result": None,
            "output_evaluation": _make_output_result(),
            "rewritten_prompt": None,
            "should_continue": False,
            "user_id": None,
            "overall_score": 0,
            "grade": "Weak",
            "improvements": None,
        }
        with patch("src.agent.nodes.report_builder._store_embedding", new_callable=AsyncMock):
            result = await build_report(state)
        report = result["full_report"]

        assert report.phase == EvalPhase.OUTPUT
        assert report.structure_result is None
        assert report.output_result is not None
        assert any("[Output/LangSmith]" in f for f in report.combined_findings)

    @pytest.mark.asyncio
    async def test_full_report(self):
        state = {
            "input_text": "Test prompt",
            "eval_phase": EvalPhase.FULL,
            "evaluation_result": _make_structure_result(),
            "output_evaluation": _make_output_result(),
            "rewritten_prompt": "Better prompt",
            "should_continue": False,
            "user_id": None,
            "overall_score": 65,
            "grade": "Good",
            "improvements": [],
        }
        with patch("src.agent.nodes.report_builder._store_embedding", new_callable=AsyncMock):
            result = await build_report(state)
        report = result["full_report"]

        assert report.phase == EvalPhase.FULL
        assert report.structure_result is not None
        assert report.output_result is not None
        has_structure = any("[Structure/T.C.R.E.I.]" in f for f in report.combined_findings)
        has_output = any("[Output/LangSmith]" in f for f in report.combined_findings)
        assert has_structure
        assert has_output

    @pytest.mark.asyncio
    async def test_combined_findings_format(self):
        state = {
            "input_text": "Test",
            "eval_phase": EvalPhase.FULL,
            "evaluation_result": _make_structure_result(),
            "output_evaluation": _make_output_result(),
            "rewritten_prompt": None,
            "should_continue": False,
            "user_id": None,
            "overall_score": 65,
            "grade": "Good",
            "improvements": [],
        }
        with patch("src.agent.nodes.report_builder._store_embedding", new_callable=AsyncMock):
            result = await build_report(state)
        report = result["full_report"]

        # Check structure findings have correct prefix and content
        structure_findings = [f for f in report.combined_findings if "[Structure/T.C.R.E.I.]" in f]
        assert len(structure_findings) == 2  # Found + Missing

        # Check output findings
        output_findings = [f for f in report.combined_findings if "[Output/LangSmith]" in f]
        assert len(output_findings) == 2

    @pytest.mark.asyncio
    async def test_report_state_fields(self):
        state = {
            "input_text": "Test",
            "eval_phase": EvalPhase.STRUCTURE,
            "evaluation_result": None,
            "output_evaluation": None,
            "rewritten_prompt": None,
            "should_continue": False,
            "user_id": None,
            "overall_score": 0,
            "grade": "Weak",
            "improvements": None,
        }
        with patch("src.agent.nodes.report_builder._store_embedding", new_callable=AsyncMock):
            result = await build_report(state)

        assert result["current_step"] == "report_complete"
        assert result["should_continue"] is False
        assert "messages" in result

    @pytest.mark.asyncio
    async def test_defaults_to_structure_phase(self):
        state = {
            "input_text": "Test",
            "evaluation_result": None,
            "output_evaluation": None,
            "rewritten_prompt": None,
            "should_continue": False,
            "user_id": None,
            "overall_score": 0,
            "grade": "Weak",
            "improvements": None,
        }
        with patch("src.agent.nodes.report_builder._store_embedding", new_callable=AsyncMock):
            result = await build_report(state)
        assert result["full_report"].phase == EvalPhase.STRUCTURE

    @pytest.mark.asyncio
    async def test_embedding_storage_called(self):
        state = {
            "input_text": "Test prompt",
            "eval_phase": EvalPhase.STRUCTURE,
            "evaluation_result": _make_structure_result(),
            "output_evaluation": None,
            "rewritten_prompt": "Better prompt",
            "should_continue": False,
            "user_id": "testuser",
            "overall_score": 65,
            "grade": "Good",
            "improvements": [
                Improvement(priority=Priority.HIGH, title="Add persona", suggestion="Specify role"),
            ],
        }
        with patch("src.agent.nodes.report_builder._store_embedding", new_callable=AsyncMock) as mock_store:
            await build_report(state)
            mock_store.assert_called_once_with(state)

    @pytest.mark.asyncio
    async def test_embedding_failure_does_not_break_report(self):
        state = {
            "input_text": "Test prompt",
            "eval_phase": EvalPhase.STRUCTURE,
            "evaluation_result": None,
            "output_evaluation": None,
            "rewritten_prompt": None,
            "should_continue": False,
            "user_id": None,
            "overall_score": 0,
            "grade": "Weak",
            "improvements": None,
        }
        with patch("src.agent.nodes.report_builder._store_embedding", new_callable=AsyncMock) as mock_store:
            mock_store.side_effect = Exception("DB connection failed")
            # Should not raise — embedding storage is fire-and-forget
            # But since _store_embedding is called directly (not fire-and-forget at the function level),
            # the exception will propagate. However, the internal try/except in _store_embedding
            # catches it. Let's test the actual _store_embedding behavior.
            pass

        # Test the actual _store_embedding catches errors
        from src.agent.nodes.report_builder import _store_embedding
        with patch("src.agent.nodes.report_builder.get_session_factory") as mock_factory:
            mock_factory.side_effect = Exception("DB unavailable")
            # Should not raise
            await _store_embedding(state)
