"""Unit tests for the analyzer node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.nodes.analyzer import (
    _build_criteria_description,
    _empty_analysis,
    _format_historical_context,
    _map_analysis_response,
    analyze_prompt,
    analyze_system_prompt,
)
from src.evaluator.llm_schemas import (
    AnalysisLLMResponse,
    DimensionLLMResponse,
    SubCriterionLLMResponse,
    TCREIFlagsLLMResponse,
)


class TestMapAnalysisResponse:
    def test_maps_full_response(self):
        response = AnalysisLLMResponse(
            dimensions={
                "task": DimensionLLMResponse(
                    score=75,
                    sub_criteria=[SubCriterionLLMResponse(name="clear_action_verb", found=True, detail="Found verb")],
                ),
                "context": DimensionLLMResponse(score=50, sub_criteria=[]),
                "references": DimensionLLMResponse(score=20, sub_criteria=[]),
                "constraints": DimensionLLMResponse(score=60, sub_criteria=[]),
            },
            tcrei_flags=TCREIFlagsLLMResponse(task=True, context=False),
        )
        result = _map_analysis_response(response)
        assert len(result["dimensions"]) == 4
        assert result["dimensions"][0].name == "task"
        assert result["dimensions"][0].score == 75
        assert result["dimensions"][0].sub_criteria[0].name == "clear_action_verb"
        assert result["tcrei_flags"].task is True
        assert result["tcrei_flags"].context is False

    def test_missing_dimension_defaults_to_zero(self):
        response = AnalysisLLMResponse(
            dimensions={"task": DimensionLLMResponse(score=80, sub_criteria=[])},
            tcrei_flags=TCREIFlagsLLMResponse(),
        )
        result = _map_analysis_response(response)
        assert len(result["dimensions"]) == 4
        # task is present
        assert result["dimensions"][0].score == 80
        # context, references, constraints default to 0
        assert result["dimensions"][1].score == 0
        assert result["dimensions"][2].score == 0
        assert result["dimensions"][3].score == 0

    def test_empty_response(self):
        response = AnalysisLLMResponse()
        result = _map_analysis_response(response)
        assert len(result["dimensions"]) == 4
        for dim in result["dimensions"]:
            assert dim.score == 0

    def test_preserves_all_sub_criteria(self):
        response = AnalysisLLMResponse(
            dimensions={
                "task": DimensionLLMResponse(
                    score=90,
                    sub_criteria=[
                        SubCriterionLLMResponse(name="a", found=True, detail="yes"),
                        SubCriterionLLMResponse(name="b", found=False, detail="no"),
                    ],
                ),
                "context": DimensionLLMResponse(score=0, sub_criteria=[]),
                "references": DimensionLLMResponse(score=0, sub_criteria=[]),
                "constraints": DimensionLLMResponse(score=0, sub_criteria=[]),
            },
            tcrei_flags=TCREIFlagsLLMResponse(),
        )
        result = _map_analysis_response(response)
        assert len(result["dimensions"][0].sub_criteria) == 2


class TestEmptyAnalysis:
    def test_returns_four_dimensions(self):
        result = _empty_analysis()
        assert len(result["dimensions"]) == 4

    def test_all_scores_zero(self):
        result = _empty_analysis()
        for dim in result["dimensions"]:
            assert dim.score == 0

    def test_all_sub_criteria_empty(self):
        result = _empty_analysis()
        for dim in result["dimensions"]:
            assert dim.sub_criteria == []

    def test_tcrei_flags_all_false(self):
        result = _empty_analysis()
        flags = result["tcrei_flags"]
        assert not flags.task
        assert not flags.context
        assert not flags.references
        assert not flags.evaluate
        assert not flags.iterate

    def test_dimension_names(self):
        result = _empty_analysis()
        names = [d.name for d in result["dimensions"]]
        assert names == ["task", "context", "references", "constraints"]


class TestBuildCriteriaDescription:
    def test_includes_all_dimensions(self):
        desc = _build_criteria_description()
        assert "TASK" in desc
        assert "CONTEXT" in desc
        assert "REFERENCES" in desc
        assert "CONSTRAINTS" in desc

    def test_includes_criteria_names(self):
        desc = _build_criteria_description()
        assert "clear_action_verb" in desc
        assert "background_provided" in desc
        assert "examples_included" in desc
        assert "scope_boundaries" in desc

    def test_includes_detection_hints(self):
        desc = _build_criteria_description()
        assert "hint:" in desc

    def test_email_task_type_includes_email_criteria(self):
        desc = _build_criteria_description("email_writing")
        assert "email_action_specified" in desc
        assert "tone_style_defined" in desc
        assert "recipient_defined" in desc
        assert "email_examples_provided" in desc
        assert "length_brevity" in desc

    def test_email_task_type_excludes_general_criteria(self):
        desc = _build_criteria_description("email_writing")
        assert "clear_action_verb" not in desc
        assert "background_provided" not in desc
        assert "examples_included" not in desc

    def test_summarization_task_type_includes_summarization_criteria(self):
        desc = _build_criteria_description("summarization")
        assert "content_scope_specified" in desc
        assert "format_and_tone_defined" in desc
        assert "source_document_described" in desc
        assert "source_material_provided" in desc
        assert "length_word_limits" in desc

    def test_summarization_task_type_excludes_general_criteria(self):
        desc = _build_criteria_description("summarization")
        assert "clear_action_verb" not in desc
        assert "background_provided" not in desc
        assert "examples_included" not in desc


class TestFormatHistoricalContext:
    def test_formats_similar_evaluations(self):
        similar = [
            {
                "input_text": "Write about cats for pet owners",
                "overall_score": 72,
                "grade": "Good",
                "improvements_summary": "Add persona and constraints",
                "rewritten_prompt": "As a pet expert...",
                "distance": 0.15,
            },
        ]
        result = _format_historical_context(similar)
        assert "Lessons from Previous Evaluations" in result
        assert "72/100" in result
        assert "Good" in result
        assert "Add persona" in result

    def test_empty_list(self):
        result = _format_historical_context([])
        assert "Lessons from Previous Evaluations" in result

    def test_truncates_to_three(self):
        similar = [
            {
                "input_text": f"Prompt {i}",
                "overall_score": 50 + i,
                "grade": "Good",
                "improvements_summary": None,
                "rewritten_prompt": None,
                "distance": 0.1 * i,
            }
            for i in range(5)
        ]
        result = _format_historical_context(similar)
        assert "1." in result
        assert "2." in result
        assert "3." in result
        assert "4." not in result


class TestAnalyzePrompt:
    @pytest.mark.asyncio
    async def test_analyze_prompt_returns_dimensions(self):
        mock_response = AnalysisLLMResponse(
            dimensions={
                "task": DimensionLLMResponse(score=70, sub_criteria=[]),
                "context": DimensionLLMResponse(score=50, sub_criteria=[]),
                "references": DimensionLLMResponse(score=20, sub_criteria=[]),
                "constraints": DimensionLLMResponse(score=60, sub_criteria=[]),
            },
            tcrei_flags=TCREIFlagsLLMResponse(task=True),
        )

        with patch("src.agent.nodes.analyzer.get_llm") as mock_llm, \
             patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.analyzer.retrieve_context", new_callable=AsyncMock, return_value=""), \
             patch("src.agent.nodes.analyzer._retrieve_similar_evaluations", new_callable=AsyncMock, return_value=[]):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {"input_text": "Write me something about dogs", "mode": "prompt", "user_id": None}
            result = await analyze_prompt(state)

            assert "dimension_scores" in result
            assert len(result["dimension_scores"]) == 4
            assert result["current_step"] == "analysis_complete"

    @pytest.mark.asyncio
    async def test_analyze_prompt_fallback_on_none(self):
        with patch("src.agent.nodes.analyzer.get_llm") as mock_llm, \
             patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.analyzer.retrieve_context", new_callable=AsyncMock, return_value=""), \
             patch("src.agent.nodes.analyzer._retrieve_similar_evaluations", new_callable=AsyncMock, return_value=[]):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = None

            state = {"input_text": "bad prompt", "mode": "prompt", "user_id": None}
            result = await analyze_prompt(state)

            assert len(result["dimension_scores"]) == 4
            for dim in result["dimension_scores"]:
                assert dim.score == 0

    @pytest.mark.asyncio
    async def test_analyze_prompt_with_similar_evaluations(self):
        mock_response = AnalysisLLMResponse(
            dimensions={
                "task": DimensionLLMResponse(score=70, sub_criteria=[]),
                "context": DimensionLLMResponse(score=50, sub_criteria=[]),
                "references": DimensionLLMResponse(score=20, sub_criteria=[]),
                "constraints": DimensionLLMResponse(score=60, sub_criteria=[]),
            },
            tcrei_flags=TCREIFlagsLLMResponse(task=True),
        )

        similar = [
            {
                "input_text": "Write about cats",
                "overall_score": 72,
                "grade": "Good",
                "improvements_summary": "Add persona",
                "rewritten_prompt": "As a vet...",
                "distance": 0.15,
            },
        ]

        with patch("src.agent.nodes.analyzer.get_llm") as mock_llm, \
             patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.analyzer.retrieve_context", new_callable=AsyncMock, return_value=""), \
             patch("src.agent.nodes.analyzer._retrieve_similar_evaluations", new_callable=AsyncMock, return_value=similar):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {"input_text": "Write me something about dogs", "mode": "prompt", "user_id": None}
            result = await analyze_prompt(state)

            assert result["similar_evaluations"] == similar
            assert "dimension_scores" in result

    @pytest.mark.asyncio
    async def test_analyze_prompt_email_task_type_uses_email_prompt(self):
        from src.evaluator import TaskType

        mock_response = AnalysisLLMResponse(
            dimensions={
                "task": DimensionLLMResponse(score=70, sub_criteria=[]),
                "context": DimensionLLMResponse(score=50, sub_criteria=[]),
                "references": DimensionLLMResponse(score=20, sub_criteria=[]),
                "constraints": DimensionLLMResponse(score=60, sub_criteria=[]),
            },
            tcrei_flags=TCREIFlagsLLMResponse(task=True),
        )

        with patch("src.agent.nodes.analyzer.get_llm") as mock_llm, \
             patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.analyzer.retrieve_context", new_callable=AsyncMock, return_value=""), \
             patch("src.agent.nodes.analyzer._retrieve_similar_evaluations", new_callable=AsyncMock, return_value=[]):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Write an email to my manager asking for PTO",
                "mode": "prompt",
                "user_id": None,
                "task_type": TaskType.EMAIL_WRITING,
            }
            result = await analyze_prompt(state)

            assert "dimension_scores" in result
            # Verify the email analysis prompt was used via the system message
            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert "email" in system_msg.content.lower()

    @pytest.mark.asyncio
    async def test_analyze_prompt_general_task_type_uses_default_prompt(self):
        from src.evaluator import TaskType

        mock_response = AnalysisLLMResponse(
            dimensions={
                "task": DimensionLLMResponse(score=70, sub_criteria=[]),
                "context": DimensionLLMResponse(score=50, sub_criteria=[]),
                "references": DimensionLLMResponse(score=20, sub_criteria=[]),
                "constraints": DimensionLLMResponse(score=60, sub_criteria=[]),
            },
            tcrei_flags=TCREIFlagsLLMResponse(task=True),
        )

        with patch("src.agent.nodes.analyzer.get_llm") as mock_llm, \
             patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.analyzer.retrieve_context", new_callable=AsyncMock, return_value=""), \
             patch("src.agent.nodes.analyzer._retrieve_similar_evaluations", new_callable=AsyncMock, return_value=[]):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Write a blog post about dogs",
                "mode": "prompt",
                "user_id": None,
                "task_type": TaskType.GENERAL,
            }
            result = await analyze_prompt(state)

            assert "dimension_scores" in result
            # Verify the default ANALYSIS_SYSTEM_PROMPT was used (not email)
            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert "email communication coach" not in system_msg.content

    @pytest.mark.asyncio
    async def test_analyze_prompt_summarization_task_type_uses_summarization_prompt(self):
        from src.evaluator import TaskType

        mock_response = AnalysisLLMResponse(
            dimensions={
                "task": DimensionLLMResponse(score=70, sub_criteria=[]),
                "context": DimensionLLMResponse(score=50, sub_criteria=[]),
                "references": DimensionLLMResponse(score=20, sub_criteria=[]),
                "constraints": DimensionLLMResponse(score=60, sub_criteria=[]),
            },
            tcrei_flags=TCREIFlagsLLMResponse(task=True),
        )

        with patch("src.agent.nodes.analyzer.get_llm") as mock_llm, \
             patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.analyzer.retrieve_context", new_callable=AsyncMock, return_value=""), \
             patch("src.agent.nodes.analyzer._retrieve_similar_evaluations", new_callable=AsyncMock, return_value=[]):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Summarize this research paper into key takeaways",
                "mode": "prompt",
                "user_id": None,
                "task_type": TaskType.SUMMARIZATION,
            }
            result = await analyze_prompt(state)

            assert "dimension_scores" in result
            # Verify the summarization analysis prompt was used via the system message
            call_prompt = mock_invoke.call_args[0][1]
            system_msg = call_prompt.messages[0]
            assert "summarization" in system_msg.content.lower()

    @pytest.mark.asyncio
    async def test_analyze_system_prompt_returns_dimensions(self):
        mock_response = AnalysisLLMResponse(
            dimensions={
                "task": DimensionLLMResponse(score=85, sub_criteria=[]),
                "context": DimensionLLMResponse(score=80, sub_criteria=[]),
                "references": DimensionLLMResponse(score=40, sub_criteria=[]),
                "constraints": DimensionLLMResponse(score=75, sub_criteria=[]),
            },
            tcrei_flags=TCREIFlagsLLMResponse(task=True, context=True, references=True, evaluate=True),
        )

        with patch("src.agent.nodes.analyzer.get_llm") as mock_llm, \
             patch("src.agent.nodes.analyzer.invoke_structured", new_callable=AsyncMock) as mock_invoke, \
             patch("src.agent.nodes.analyzer.retrieve_context", new_callable=AsyncMock, return_value=""):
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "You are a medical assistant",
                "mode": "system_prompt",
                "expected_outcome": "Structured SOAP notes",
            }
            result = await analyze_system_prompt(state)

            assert "dimension_scores" in result
            assert result["tcrei_flags"].task is True
            assert result["current_step"] == "analysis_complete"
