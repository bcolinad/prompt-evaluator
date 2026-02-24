"""Unit tests for PromptEvaluationService."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.evaluator import (
    EvalPhase,
    FullEvaluationReport,
    MetaAssessment,
    OutputEvaluationResult,
)
from src.evaluator.service import EvaluationReport, PromptEvaluationService
from src.evaluator.strategies import StrategyConfig, get_default_strategy


class TestEvaluationReport:
    def test_defaults(self):
        report = EvaluationReport()
        assert report.full_report is None
        assert report.overall_score == 0
        assert report.grade == "Weak"
        assert report.strategy_used == "enhanced (CoT+ToT+Meta)"
        assert report.meta_assessment is None
        assert report.optimized_output_evaluation is None
        assert report.error is None

    def test_with_error(self):
        report = EvaluationReport(error="Something failed")
        assert report.error == "Something failed"
        assert report.full_report is None

    def test_optimized_output_evaluation_field(self):
        """optimized_output_evaluation can be set and retrieved."""
        mock_output_eval = OutputEvaluationResult(
            prompt_used="test prompt",
            llm_output="test output",
            provider="google",
            model="gemini-2.0-flash",
            dimensions=[],
            overall_score=0.85,
            grade="Good",
        )
        report = EvaluationReport(optimized_output_evaluation=mock_output_eval)
        assert report.optimized_output_evaluation is not None
        assert report.optimized_output_evaluation.overall_score == 0.85
        assert report.optimized_output_evaluation.provider == "google"


class TestPromptEvaluationService:
    def test_init_defaults(self):
        svc = PromptEvaluationService()
        assert svc.llm_provider == "google"

    def test_init_custom_provider(self):
        svc = PromptEvaluationService(llm_provider="anthropic")
        assert svc.llm_provider == "anthropic"


class TestEvaluateMethod:
    @pytest.mark.asyncio
    async def test_success_returns_report(self):
        full_report = FullEvaluationReport(
            phase=EvalPhase.FULL,
            input_text="test prompt",
            strategy_used="enhanced (CoT+ToT+Meta)",
        )

        async def mock_stream(initial_state, stream_mode=None):
            yield {"build_report": {
                "full_report": full_report,
                "overall_score": 75,
                "grade": "Good",
            }}

        mock_graph = AsyncMock()
        mock_graph.astream = mock_stream

        with patch("src.evaluator.service.get_graph", return_value=mock_graph):
            svc = PromptEvaluationService()
            result = await svc.evaluate("test prompt")

        assert result.error is None
        assert result.full_report is full_report
        assert result.overall_score == 75
        assert result.grade == "Good"

    @pytest.mark.asyncio
    async def test_fatal_error_returns_error_report(self):
        async def mock_stream(initial_state, stream_mode=None):
            yield {"analyze_prompt": {"error_message": "Fatal: billing issue"}}

        mock_graph = AsyncMock()
        mock_graph.astream = mock_stream

        with patch("src.evaluator.service.get_graph", return_value=mock_graph):
            svc = PromptEvaluationService()
            result = await svc.evaluate("test prompt")

        assert result.error == "Fatal: billing issue"
        assert result.full_report is None

    @pytest.mark.asyncio
    async def test_no_report_returns_error(self):
        async def mock_stream(initial_state, stream_mode=None):
            yield {"build_report": {"some_key": "but no full_report"}}

        mock_graph = AsyncMock()
        mock_graph.astream = mock_stream

        with patch("src.evaluator.service.get_graph", return_value=mock_graph):
            svc = PromptEvaluationService()
            result = await svc.evaluate("test prompt")

        assert result.error == "Evaluation produced no report."

    @pytest.mark.asyncio
    async def test_unexpected_exception_returns_error(self):
        async def mock_stream(initial_state, stream_mode=None):
            raise RuntimeError("connection lost")
            yield  # make it a generator

        mock_graph = AsyncMock()
        mock_graph.astream = mock_stream

        with patch("src.evaluator.service.get_graph", return_value=mock_graph):
            svc = PromptEvaluationService()
            result = await svc.evaluate("test prompt")

        assert result.error is not None
        assert "RuntimeError" in result.error

    @pytest.mark.asyncio
    async def test_default_strategy_always_used(self):
        """Service always uses get_default_strategy() internally."""
        captured_state = {}

        async def mock_stream(initial_state, stream_mode=None):
            captured_state.update(initial_state)
            yield {"build_report": {
                "full_report": FullEvaluationReport(
                    phase=EvalPhase.FULL,
                    input_text="test",
                    strategy_used="enhanced (CoT+ToT+Meta)",
                ),
            }}

        mock_graph = AsyncMock()
        mock_graph.astream = mock_stream

        with patch("src.evaluator.service.get_graph", return_value=mock_graph):
            svc = PromptEvaluationService()
            await svc.evaluate("test")

        strategy = captured_state.get("strategy")
        expected = get_default_strategy()
        assert isinstance(strategy, StrategyConfig)
        assert strategy.use_cot is expected.use_cot
        assert strategy.use_tot is expected.use_tot
        assert strategy.use_meta is expected.use_meta

    @pytest.mark.asyncio
    async def test_execution_count_passed_to_initial_state(self):
        """execution_count parameter is forwarded into the graph initial state."""
        captured_state = {}

        async def mock_stream(initial_state, stream_mode=None):
            captured_state.update(initial_state)
            yield {"build_report": {
                "full_report": FullEvaluationReport(
                    phase=EvalPhase.FULL,
                    input_text="test",
                    strategy_used="enhanced (CoT+ToT+Meta)",
                ),
            }}

        mock_graph = AsyncMock()
        mock_graph.astream = mock_stream

        with patch("src.evaluator.service.get_graph", return_value=mock_graph):
            svc = PromptEvaluationService()
            await svc.evaluate("test", execution_count=4)

        assert captured_state["execution_count"] == 4

    @pytest.mark.asyncio
    async def test_execution_count_defaults_to_two(self):
        """execution_count defaults to 2 when not specified."""
        captured_state = {}

        async def mock_stream(initial_state, stream_mode=None):
            captured_state.update(initial_state)
            yield {"build_report": {
                "full_report": FullEvaluationReport(
                    phase=EvalPhase.FULL,
                    input_text="test",
                    strategy_used="enhanced (CoT+ToT+Meta)",
                ),
            }}

        mock_graph = AsyncMock()
        mock_graph.astream = mock_stream

        with patch("src.evaluator.service.get_graph", return_value=mock_graph):
            svc = PromptEvaluationService()
            await svc.evaluate("test")

        assert captured_state["execution_count"] == 2

    @pytest.mark.asyncio
    async def test_meta_assessment_propagated(self):
        meta = MetaAssessment(
            accuracy_score=0.9,
            completeness_score=0.85,
            actionability_score=0.8,
            faithfulness_score=0.95,
            overall_confidence=0.88,
        )
        full_report = FullEvaluationReport(
            phase=EvalPhase.FULL,
            input_text="test",
            meta_assessment=meta,
            strategy_used="enhanced (CoT+ToT+Meta)",
        )

        async def mock_stream(initial_state, stream_mode=None):
            yield {"build_report": {
                "full_report": full_report,
                "meta_assessment": meta,
                "overall_score": 80,
                "grade": "Good",
            }}

        mock_graph = AsyncMock()
        mock_graph.astream = mock_stream

        with patch("src.evaluator.service.get_graph", return_value=mock_graph):
            svc = PromptEvaluationService()
            result = await svc.evaluate("test")

        assert result.meta_assessment is not None
        assert result.meta_assessment.overall_confidence == 0.88
        assert result.strategy_used == "enhanced (CoT+ToT+Meta)"

    @pytest.mark.asyncio
    async def test_llm_provider_override(self):
        captured_state = {}

        async def mock_stream(initial_state, stream_mode=None):
            captured_state.update(initial_state)
            yield {"build_report": {
                "full_report": FullEvaluationReport(
                    phase=EvalPhase.FULL,
                    input_text="test",
                    strategy_used="enhanced (CoT+ToT+Meta)",
                ),
            }}

        mock_graph = AsyncMock()
        mock_graph.astream = mock_stream

        with patch("src.evaluator.service.get_graph", return_value=mock_graph):
            svc = PromptEvaluationService(llm_provider="google")
            await svc.evaluate("test", llm_provider="anthropic")

        assert captured_state["llm_provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_optimized_output_evaluation_propagated(self):
        """optimized_output_evaluation from graph state is propagated to the report."""
        optimized_eval = OutputEvaluationResult(
            prompt_used="optimized prompt",
            llm_output="better output",
            provider="google",
            model="gemini-2.0-flash",
            dimensions=[],
            overall_score=0.92,
            grade="Excellent",
        )
        full_report = FullEvaluationReport(
            phase=EvalPhase.FULL,
            input_text="test",
            strategy_used="enhanced (CoT+ToT+Meta)",
        )

        async def mock_stream(initial_state, stream_mode=None):
            yield {"build_report": {
                "full_report": full_report,
                "overall_score": 85,
                "grade": "Excellent",
                "optimized_output_evaluation": optimized_eval,
            }}

        mock_graph = AsyncMock()
        mock_graph.astream = mock_stream

        with patch("src.evaluator.service.get_graph", return_value=mock_graph):
            svc = PromptEvaluationService()
            result = await svc.evaluate("test")

        assert result.optimized_output_evaluation is not None
        assert result.optimized_output_evaluation.overall_score == 0.92
        assert result.optimized_output_evaluation.grade == "Excellent"
