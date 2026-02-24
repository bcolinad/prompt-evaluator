"""Unit tests for the improver node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.nodes.improver import (
    _build_analysis_summary,
    _build_evaluation_result,
    _build_output_quality_summary,
    _format_historical_improvements,
    _map_improvements_response,
    generate_improvements,
)
from src.evaluator import (
    DimensionScore,
    EvalMode,
    Grade,
    Improvement,
    OutputDimensionScore,
    OutputEvaluationResult,
    Priority,
    SubCriterionResult,
    TCREIFlags,
)
from src.evaluator.llm_schemas import ImprovementLLMResponse, ImprovementsLLMResponse
from src.prompts import (
    EMAIL_IMPROVEMENT_GUIDANCE,
    PROMPT_TYPE_CONTINUATION,
    PROMPT_TYPE_INITIAL,
    SUMMARIZATION_IMPROVEMENT_GUIDANCE,
)


class TestBuildAnalysisSummary:
    def test_formats_dimensions(self):
        dimensions = [
            DimensionScore(
                name="task",
                score=75,
                sub_criteria=[
                    SubCriterionResult(name="clear_action_verb", found=True, detail="Found verb 'Write'"),
                    SubCriterionResult(name="persona_defined", found=False, detail="No persona"),
                ],
            ),
            DimensionScore(name="context", score=50, sub_criteria=[]),
        ]
        result = _build_analysis_summary(dimensions)
        assert "Task" in result
        assert "75/100" in result
        assert "Found verb 'Write'" in result
        assert "No persona" in result

    def test_empty_dimensions(self):
        result = _build_analysis_summary([])
        assert result == ""

    def test_all_found(self):
        dimensions = [
            DimensionScore(
                name="task",
                score=95,
                sub_criteria=[
                    SubCriterionResult(name="test", found=True, detail="All good"),
                ],
            ),
        ]
        result = _build_analysis_summary(dimensions)
        assert "All criteria met" in result

    def test_nothing_found(self):
        dimensions = [
            DimensionScore(
                name="task",
                score=10,
                sub_criteria=[
                    SubCriterionResult(name="test", found=False, detail="Missing everything"),
                ],
            ),
        ]
        result = _build_analysis_summary(dimensions)
        assert "Nothing detected" in result


class TestMapImprovementsResponse:
    def test_maps_full_response(self):
        response = ImprovementsLLMResponse(
            improvements=[
                ImprovementLLMResponse(priority="CRITICAL", title="Add task", suggestion="Be specific"),
                ImprovementLLMResponse(priority="LOW", title="Polish", suggestion="Minor edits"),
            ],
            rewritten_prompt="Improved prompt here",
        )
        result = _map_improvements_response(response)
        assert len(result["improvements"]) == 2
        assert result["improvements"][0].priority == Priority.CRITICAL
        assert result["rewritten_prompt"] == "Improved prompt here"

    def test_empty_response(self):
        response = ImprovementsLLMResponse()
        result = _map_improvements_response(response)
        assert result["improvements"] == []
        assert result["rewritten_prompt"] is None

    def test_no_rewritten_prompt_with_improvements_logs_warning(self):
        response = ImprovementsLLMResponse(
            improvements=[ImprovementLLMResponse(priority="HIGH", title="A", suggestion="B")],
            rewritten_prompt=None,
        )
        result = _map_improvements_response(response)
        assert len(result["improvements"]) == 1
        assert result["rewritten_prompt"] is None


class TestBuildOutputQualitySummary:
    def test_formats_output_eval(self):
        output_eval = OutputEvaluationResult(
            prompt_used="test",
            llm_output="output",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            dimensions=[
                OutputDimensionScore(
                    name="relevance", score=0.90, comment="Relevant output",
                    recommendation="No change needed.",
                ),
                OutputDimensionScore(
                    name="completeness", score=0.60, comment="Missing sub-topics",
                    recommendation="Add explicit sub-topic requirements.",
                ),
            ],
            overall_score=0.75,
            grade=Grade.GOOD,
        )
        result = _build_output_quality_summary(output_eval)
        assert "75%" in result
        assert "Relevance" in result
        assert "Completeness" in result
        assert "Add explicit sub-topic requirements." in result
        # "No change needed." should NOT appear as a recommended fix
        assert "Recommended fix: No change needed." not in result

    def test_empty_dimensions(self):
        output_eval = OutputEvaluationResult(
            prompt_used="test",
            llm_output="output",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            dimensions=[],
            overall_score=0.0,
            grade=Grade.WEAK,
        )
        result = _build_output_quality_summary(output_eval)
        assert "0%" in result


class TestFormatHistoricalImprovements:
    def test_formats_improvements(self):
        similar = [
            {
                "input_text": "Write about cats",
                "overall_score": 72,
                "grade": "Good",
                "improvements_summary": "Add persona; Add constraints",
                "rewritten_prompt": "As a pet expert, write...",
                "distance": 0.15,
            },
        ]
        result = _format_historical_improvements(similar)
        assert "Effective Improvements" in result
        assert "72/100" in result
        assert "Add persona" in result

    def test_empty_when_no_improvements(self):
        similar = [
            {
                "input_text": "test",
                "overall_score": 50,
                "grade": "Needs Work",
                "improvements_summary": None,
                "rewritten_prompt": None,
                "distance": 0.2,
            },
        ]
        result = _format_historical_improvements(similar)
        assert result == ""

    def test_empty_list(self):
        result = _format_historical_improvements([])
        assert result == ""


class TestBuildEvaluationResult:
    def test_assembles_result(self):
        state = {
            "mode": EvalMode.PROMPT,
            "input_text": "Test prompt",
            "expected_outcome": None,
            "overall_score": 65,
            "grade": "Good",
            "dimension_scores": [
                DimensionScore(name="task", score=70, sub_criteria=[]),
            ],
            "tcrei_flags": TCREIFlags(task=True),
        }
        result_data = {
            "improvements": [
                Improvement(priority=Priority.MEDIUM, title="Add context", suggestion="..."),
            ],
            "rewritten_prompt": "Better prompt",
        }
        result = _build_evaluation_result(state, result_data)
        assert result.overall_score == 65
        assert result.grade == Grade.GOOD
        assert result.mode == EvalMode.PROMPT
        assert len(result.improvements) == 1
        assert result.rewritten_prompt == "Better prompt"

    def test_weak_grade(self):
        state = {
            "mode": EvalMode.PROMPT,
            "input_text": "bad",
            "expected_outcome": None,
            "overall_score": 10,
            "grade": "Weak",
            "dimension_scores": [],
            "tcrei_flags": TCREIFlags(),
        }
        result_data = {"improvements": [], "rewritten_prompt": None}
        result = _build_evaluation_result(state, result_data)
        assert result.grade == Grade.WEAK


class TestGenerateImprovements:
    @pytest.mark.asyncio
    async def test_returns_improvements(self):
        mock_response = ImprovementsLLMResponse(
            improvements=[
                ImprovementLLMResponse(priority="HIGH", title="Add persona", suggestion="Specify who the AI should act as"),
            ],
            rewritten_prompt="Improved version",
        )

        with patch("src.agent.nodes.improver.get_llm") as mock_llm, \
             patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value=""):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Write about dogs",
                "mode": EvalMode.PROMPT,
                "expected_outcome": None,
                "dimension_scores": [
                    DimensionScore(name="task", score=30, sub_criteria=[]),
                ],
                "overall_score": 25,
                "grade": "Weak",
                "tcrei_flags": TCREIFlags(),
                "output_evaluation": None,
                "similar_evaluations": None,
            }
            result = await generate_improvements(state)

            assert "improvements" in result
            assert result["rewritten_prompt"] == "Improved version"
            assert result["current_step"] == "improvements_complete"
            assert result["should_continue"] is False
            assert result["evaluation_result"] is not None

    @pytest.mark.asyncio
    async def test_fallback_on_none(self):
        with patch("src.agent.nodes.improver.get_llm") as mock_llm, \
             patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value=""):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = None

            state = {
                "input_text": "test",
                "mode": EvalMode.PROMPT,
                "expected_outcome": None,
                "dimension_scores": [],
                "overall_score": 0,
                "grade": "Weak",
                "tcrei_flags": TCREIFlags(),
                "output_evaluation": None,
                "similar_evaluations": None,
            }
            result = await generate_improvements(state)

            assert result["improvements"] == []
            assert result["rewritten_prompt"] is None

    @pytest.mark.asyncio
    async def test_with_output_evaluation(self):
        mock_response = ImprovementsLLMResponse(
            improvements=[
                ImprovementLLMResponse(priority="HIGH", title="Fix completeness", suggestion="Add sub-topic constraints"),
            ],
            rewritten_prompt="Improved with output fixes",
        )

        output_eval = OutputEvaluationResult(
            prompt_used="Write about dogs",
            llm_output="Dogs are great",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            dimensions=[
                OutputDimensionScore(name="completeness", score=0.60, comment="Missing sub-topics", recommendation="Add sub-topic requirements."),
            ],
            overall_score=0.60,
            grade=Grade.NEEDS_WORK,
        )

        with patch("src.agent.nodes.improver.get_llm") as mock_llm, \
             patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value=""):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Write about dogs",
                "mode": EvalMode.PROMPT,
                "expected_outcome": None,
                "dimension_scores": [
                    DimensionScore(name="task", score=30, sub_criteria=[]),
                ],
                "overall_score": 25,
                "grade": "Weak",
                "tcrei_flags": TCREIFlags(),
                "output_evaluation": output_eval,
                "similar_evaluations": None,
            }
            result = await generate_improvements(state)

            assert "improvements" in result
            assert result["rewritten_prompt"] == "Improved with output fixes"
            # Verify invoke_structured was called with output quality in variables
            call_vars = mock_invoke.call_args[0][2]
            assert "output_quality_section" in call_vars
            assert "Completeness" in call_vars["output_quality_section"]

    @pytest.mark.asyncio
    async def test_uses_initial_prompt_type_guidance(self):
        mock_response = ImprovementsLLMResponse(
            improvements=[],
            rewritten_prompt="Improved",
        )

        with patch("src.agent.nodes.improver.get_llm") as mock_llm, \
             patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value=""):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Write a blog post about dogs",
                "mode": EvalMode.PROMPT,
                "expected_outcome": None,
                "dimension_scores": [],
                "overall_score": 30,
                "grade": "Weak",
                "tcrei_flags": TCREIFlags(),
                "output_evaluation": None,
                "similar_evaluations": None,
                "prompt_type": "initial",
            }
            await generate_improvements(state)

            # Extract the system message content from the prompt template
            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert PROMPT_TYPE_INITIAL in system_msg.content
            assert PROMPT_TYPE_CONTINUATION not in system_msg.content

    @pytest.mark.asyncio
    async def test_uses_continuation_prompt_type_guidance(self):
        mock_response = ImprovementsLLMResponse(
            improvements=[],
            rewritten_prompt="Improved continuation",
        )

        with patch("src.agent.nodes.improver.get_llm") as mock_llm, \
             patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value=""):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Now add error handling to the code above",
                "mode": EvalMode.PROMPT,
                "expected_outcome": None,
                "dimension_scores": [],
                "overall_score": 30,
                "grade": "Weak",
                "tcrei_flags": TCREIFlags(),
                "output_evaluation": None,
                "similar_evaluations": None,
                "prompt_type": "continuation",
            }
            await generate_improvements(state)

            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert PROMPT_TYPE_CONTINUATION in system_msg.content
            assert PROMPT_TYPE_INITIAL not in system_msg.content

    @pytest.mark.asyncio
    async def test_defaults_to_initial_when_prompt_type_missing(self):
        mock_response = ImprovementsLLMResponse(
            improvements=[],
            rewritten_prompt="Improved",
        )

        with patch("src.agent.nodes.improver.get_llm") as mock_llm, \
             patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value=""):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Write about dogs",
                "mode": EvalMode.PROMPT,
                "expected_outcome": None,
                "dimension_scores": [],
                "overall_score": 30,
                "grade": "Weak",
                "tcrei_flags": TCREIFlags(),
                "output_evaluation": None,
                "similar_evaluations": None,
                # prompt_type intentionally omitted
            }
            await generate_improvements(state)

            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert PROMPT_TYPE_INITIAL in system_msg.content

    @pytest.mark.asyncio
    async def test_email_task_type_appends_email_guidance(self):
        from src.evaluator import TaskType

        mock_response = ImprovementsLLMResponse(
            improvements=[],
            rewritten_prompt="Improved email prompt",
        )

        with patch("src.agent.nodes.improver.get_llm") as mock_llm, \
             patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value=""):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Write an email to my boss",
                "mode": EvalMode.PROMPT,
                "expected_outcome": None,
                "dimension_scores": [],
                "overall_score": 30,
                "grade": "Weak",
                "tcrei_flags": TCREIFlags(),
                "output_evaluation": None,
                "similar_evaluations": None,
                "prompt_type": "initial",
                "task_type": TaskType.EMAIL_WRITING,
            }
            await generate_improvements(state)

            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert EMAIL_IMPROVEMENT_GUIDANCE in system_msg.content
            assert PROMPT_TYPE_INITIAL in system_msg.content

    @pytest.mark.asyncio
    async def test_general_task_type_does_not_append_email_guidance(self):
        from src.evaluator import TaskType

        mock_response = ImprovementsLLMResponse(
            improvements=[],
            rewritten_prompt="Improved",
        )

        with patch("src.agent.nodes.improver.get_llm") as mock_llm, \
             patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value=""):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Write a blog post",
                "mode": EvalMode.PROMPT,
                "expected_outcome": None,
                "dimension_scores": [],
                "overall_score": 30,
                "grade": "Weak",
                "tcrei_flags": TCREIFlags(),
                "output_evaluation": None,
                "similar_evaluations": None,
                "prompt_type": "initial",
                "task_type": TaskType.GENERAL,
            }
            await generate_improvements(state)

            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert EMAIL_IMPROVEMENT_GUIDANCE not in system_msg.content

    @pytest.mark.asyncio
    async def test_summarization_task_type_appends_summarization_guidance(self):
        from src.evaluator import TaskType

        mock_response = ImprovementsLLMResponse(
            improvements=[],
            rewritten_prompt="Improved summarization prompt",
        )

        with patch("src.agent.nodes.improver.get_llm") as mock_llm, \
             patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value=""):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Summarize this document",
                "mode": EvalMode.PROMPT,
                "expected_outcome": None,
                "dimension_scores": [],
                "overall_score": 30,
                "grade": "Weak",
                "tcrei_flags": TCREIFlags(),
                "output_evaluation": None,
                "similar_evaluations": None,
                "prompt_type": "initial",
                "task_type": TaskType.SUMMARIZATION,
            }
            await generate_improvements(state)

            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert SUMMARIZATION_IMPROVEMENT_GUIDANCE in system_msg.content
            assert PROMPT_TYPE_INITIAL in system_msg.content

    @pytest.mark.asyncio
    async def test_summarization_task_type_does_not_append_email_guidance(self):
        from src.evaluator import TaskType

        mock_response = ImprovementsLLMResponse(
            improvements=[],
            rewritten_prompt="Improved",
        )

        with patch("src.agent.nodes.improver.get_llm") as mock_llm, \
             patch("src.agent.nodes.improver.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.improver.retrieve_context", new_callable=AsyncMock, return_value=""):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Summarize this paper",
                "mode": EvalMode.PROMPT,
                "expected_outcome": None,
                "dimension_scores": [],
                "overall_score": 30,
                "grade": "Weak",
                "tcrei_flags": TCREIFlags(),
                "output_evaluation": None,
                "similar_evaluations": None,
                "prompt_type": "initial",
                "task_type": TaskType.SUMMARIZATION,
            }
            await generate_improvements(state)

            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert EMAIL_IMPROVEMENT_GUIDANCE not in system_msg.content
