"""Unit tests for the output evaluator node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.nodes.output_evaluator import (
    _empty_output_evaluation,
    _map_output_evaluation,
    _score_to_grade,
    evaluate_output,
)
from src.evaluator import Grade
from src.evaluator.llm_schemas import (
    OutputDimensionLLMResponse,
    OutputEvaluationLLMResponse,
)

VALID_PARSED = OutputEvaluationLLMResponse(
    dimensions=[
        OutputDimensionLLMResponse(name="relevance", score=0.85, comment="Directly addresses dogs topic", recommendation="No change needed."),
        OutputDimensionLLMResponse(name="coherence", score=0.90, comment="Well-structured", recommendation="No change needed."),
        OutputDimensionLLMResponse(name="completeness", score=0.70, comment="Main points covered", recommendation="Add explicit requirements for sub-topics."),
        OutputDimensionLLMResponse(name="instruction_following", score=0.80, comment="Follows format", recommendation="Specify output format constraints."),
        OutputDimensionLLMResponse(name="hallucination_risk", score=0.95, comment="No fabrication", recommendation="No change needed."),
    ],
    overall_score=0.84,
    findings=["Evaluated using LangSmith LLM-as-Judge scoring.", "Good output overall."],
)


class TestMapOutputEvaluation:
    @patch("src.agent.nodes.output_evaluator.get_settings")
    def test_maps_parsed_response(self, mock_settings):
        settings = MagicMock()
        settings.llm_provider.value = "anthropic"
        settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.return_value = settings

        state = {"input_text": "Write about dogs", "llm_output": "Dogs are great"}
        result = _map_output_evaluation(VALID_PARSED, state, "run-123")

        assert len(result.dimensions) == 5
        assert result.dimensions[0].name == "relevance"
        assert result.dimensions[0].score == 0.85
        assert result.dimensions[0].recommendation == "No change needed."
        assert result.dimensions[2].recommendation == "Add explicit requirements for sub-topics."
        assert result.overall_score == 0.84
        assert result.grade == Grade.GOOD
        assert result.langsmith_run_id == "run-123"
        assert len(result.findings) == 2


class TestScoreToGrade:
    def test_excellent(self):
        assert _score_to_grade(0.90) == Grade.EXCELLENT
        assert _score_to_grade(0.85) == Grade.EXCELLENT
        assert _score_to_grade(1.0) == Grade.EXCELLENT

    def test_good(self):
        assert _score_to_grade(0.84) == Grade.GOOD
        assert _score_to_grade(0.65) == Grade.GOOD
        assert _score_to_grade(0.70) == Grade.GOOD

    def test_needs_work(self):
        assert _score_to_grade(0.64) == Grade.NEEDS_WORK
        assert _score_to_grade(0.40) == Grade.NEEDS_WORK
        assert _score_to_grade(0.50) == Grade.NEEDS_WORK

    def test_weak(self):
        assert _score_to_grade(0.39) == Grade.WEAK
        assert _score_to_grade(0.0) == Grade.WEAK
        assert _score_to_grade(0.10) == Grade.WEAK


class TestEmptyOutputEvaluation:
    @patch("src.agent.nodes.output_evaluator.get_settings")
    def test_returns_fallback_with_five_dimensions(self, mock_settings):
        settings = MagicMock()
        settings.llm_provider.value = "anthropic"
        settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.return_value = settings

        state = {"input_text": "Test", "llm_output": "Output"}
        result = _empty_output_evaluation(state, "run-456")

        assert len(result.dimensions) == 5
        assert result.dimensions[0].name == "relevance"
        assert result.dimensions[1].name == "coherence"
        assert result.dimensions[2].name == "completeness"
        assert result.dimensions[3].name == "instruction_following"
        assert result.dimensions[4].name == "hallucination_risk"
        assert all(d.score == 0.0 for d in result.dimensions)
        assert all(d.recommendation != "" for d in result.dimensions)
        assert result.overall_score == 0.0
        assert result.grade == Grade.WEAK
        assert result.langsmith_run_id == "run-456"
        assert "Evaluation failed" in result.findings[0]

    @patch("src.agent.nodes.output_evaluator.get_settings")
    def test_returns_email_fallback_dimensions_for_email_task_type(self, mock_settings):
        settings = MagicMock()
        settings.llm_provider.value = "anthropic"
        settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.return_value = settings

        state = {"input_text": "Test", "llm_output": "Output"}
        result = _empty_output_evaluation(state, "run-789", task_type="email_writing")

        assert len(result.dimensions) == 5
        assert result.dimensions[0].name == "tone_appropriateness"
        assert result.dimensions[1].name == "professional_email_structure"
        assert result.dimensions[2].name == "audience_fit"
        assert result.dimensions[3].name == "purpose_achievement"
        assert result.dimensions[4].name == "conciseness_clarity"
        assert all(d.score == 0.0 for d in result.dimensions)


    @patch("src.agent.nodes.output_evaluator.get_settings")
    def test_returns_summarization_fallback_dimensions_for_summarization_task_type(self, mock_settings):
        settings = MagicMock()
        settings.llm_provider.value = "anthropic"
        settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.return_value = settings

        state = {"input_text": "Test", "llm_output": "Output"}
        result = _empty_output_evaluation(state, "run-101", task_type="summarization")

        assert len(result.dimensions) == 5
        assert result.dimensions[0].name == "information_accuracy"
        assert result.dimensions[1].name == "logical_structure"
        assert result.dimensions[2].name == "key_information_coverage"
        assert result.dimensions[3].name == "source_fidelity"
        assert result.dimensions[4].name == "conciseness_precision"
        assert all(d.score == 0.0 for d in result.dimensions)


class TestEvaluateOutput:
    @pytest.mark.asyncio
    async def test_evaluate_output_success(self):
        """Test success path using invoke_structured."""
        mock_settings = MagicMock()
        mock_settings.llm_provider.value = "anthropic"
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"

        with patch("src.agent.nodes.output_evaluator.get_llm") as mock_get_llm, \
             patch("src.agent.nodes.output_evaluator.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.output_evaluator.collect_runs") as mock_collect, \
             patch("src.agent.nodes.output_evaluator.score_run"), \
             patch("src.agent.nodes.output_evaluator.get_settings", return_value=mock_settings):
            mock_get_llm.return_value = MagicMock()
            mock_invoke.return_value = VALID_PARSED

            mock_cb = MagicMock()
            mock_cb.traced_runs = []
            mock_collect.return_value.__enter__ = MagicMock(return_value=mock_cb)
            mock_collect.return_value.__exit__ = MagicMock(return_value=False)

            state = {"input_text": "Write about dogs", "llm_output": "Dogs are great", "session_id": "test"}
            result = await evaluate_output(state)

            assert "output_evaluation" in result
            assert result["current_step"] == "output_evaluated"
            assert result["output_evaluation"].overall_score == 0.84
            assert len(result["output_evaluation"].dimensions) == 5

    @pytest.mark.asyncio
    async def test_evaluate_output_total_failure(self):
        """Test that total parsing failure returns fallback with 5 dimensions."""
        mock_settings = MagicMock()
        mock_settings.llm_provider.value = "anthropic"
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"

        with patch("src.agent.nodes.output_evaluator.get_llm") as mock_get_llm, \
             patch("src.agent.nodes.output_evaluator.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.output_evaluator.collect_runs") as mock_collect, \
             patch("src.agent.nodes.output_evaluator.score_run"), \
             patch("src.agent.nodes.output_evaluator.get_settings", return_value=mock_settings):
            mock_get_llm.return_value = MagicMock()
            mock_invoke.return_value = None  # Total failure

            mock_cb = MagicMock()
            mock_cb.traced_runs = []
            mock_collect.return_value.__enter__ = MagicMock(return_value=mock_cb)
            mock_collect.return_value.__exit__ = MagicMock(return_value=False)

            state = {"input_text": "Test", "llm_output": "Output", "session_id": "test"}
            result = await evaluate_output(state)

            assert result["output_evaluation"].overall_score == 0.0
            assert result["output_evaluation"].grade == Grade.WEAK
            assert len(result["output_evaluation"].dimensions) == 5

    @pytest.mark.asyncio
    async def test_evaluate_output_email_task_type_uses_email_prompt(self):
        """Test that email task type selects the email output evaluation prompt."""
        from src.evaluator import TaskType

        mock_settings = MagicMock()
        mock_settings.llm_provider.value = "anthropic"
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"

        with patch("src.agent.nodes.output_evaluator.get_llm") as mock_get_llm, \
             patch("src.agent.nodes.output_evaluator.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.output_evaluator.collect_runs") as mock_collect, \
             patch("src.agent.nodes.output_evaluator.score_run"), \
             patch("src.agent.nodes.output_evaluator.get_settings", return_value=mock_settings):
            mock_get_llm.return_value = MagicMock()
            mock_invoke.return_value = VALID_PARSED

            mock_cb = MagicMock()
            mock_cb.traced_runs = []
            mock_collect.return_value.__enter__ = MagicMock(return_value=mock_cb)
            mock_collect.return_value.__exit__ = MagicMock(return_value=False)

            state = {
                "input_text": "Write an email to my manager",
                "llm_output": "Dear Manager, ...",
                "session_id": "test",
                "task_type": TaskType.EMAIL_WRITING,
            }
            result = await evaluate_output(state)

            assert "output_evaluation" in result
            # Verify email prompt was used via the system message
            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert "Tone Appropriateness" in system_msg.content

    @pytest.mark.asyncio
    async def test_evaluate_output_summarization_task_type_uses_summarization_prompt(self):
        """Test that summarization task type selects the summarization output evaluation prompt."""
        from src.evaluator import TaskType

        mock_settings = MagicMock()
        mock_settings.llm_provider.value = "anthropic"
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"

        with patch("src.agent.nodes.output_evaluator.get_llm") as mock_get_llm, \
             patch("src.agent.nodes.output_evaluator.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.output_evaluator.collect_runs") as mock_collect, \
             patch("src.agent.nodes.output_evaluator.score_run"), \
             patch("src.agent.nodes.output_evaluator.get_settings", return_value=mock_settings):
            mock_get_llm.return_value = MagicMock()
            mock_invoke.return_value = VALID_PARSED

            mock_cb = MagicMock()
            mock_cb.traced_runs = []
            mock_collect.return_value.__enter__ = MagicMock(return_value=mock_cb)
            mock_collect.return_value.__exit__ = MagicMock(return_value=False)

            state = {
                "input_text": "Summarize this document",
                "llm_output": "The document covers...",
                "session_id": "test",
                "task_type": TaskType.SUMMARIZATION,
            }
            result = await evaluate_output(state)

            assert "output_evaluation" in result
            # Verify summarization prompt was used via the system message
            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert "Information Accuracy" in system_msg.content

    @pytest.mark.asyncio
    async def test_scores_dimensions_in_langsmith(self):
        """Test that LangSmith scoring is called for each dimension."""
        mock_settings = MagicMock()
        mock_settings.llm_provider.value = "anthropic"
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"

        mock_run = MagicMock()
        mock_run.id = "traced-run-id"

        with patch("src.agent.nodes.output_evaluator.get_llm") as mock_get_llm, \
             patch("src.agent.nodes.output_evaluator.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.output_evaluator.collect_runs") as mock_collect, \
             patch("src.agent.nodes.output_evaluator.score_run") as mock_score, \
             patch("src.agent.nodes.output_evaluator.get_settings", return_value=mock_settings):
            mock_get_llm.return_value = MagicMock()
            mock_invoke.return_value = VALID_PARSED

            mock_cb = MagicMock()
            mock_cb.traced_runs = [mock_run]
            mock_collect.return_value.__enter__ = MagicMock(return_value=mock_cb)
            mock_collect.return_value.__exit__ = MagicMock(return_value=False)

            state = {"input_text": "Write about dogs", "llm_output": "Dogs are great", "session_id": "test"}
            await evaluate_output(state)

            assert mock_score.call_count == 5
