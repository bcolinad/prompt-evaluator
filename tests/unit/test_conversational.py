"""Unit tests for the conversational follow-up node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.nodes.conversational import (
    _build_dimension_summary,
    _build_improvements_summary,
    _build_state_update,
    _get_latest_user_message,
    _map_followup_response,
    handle_followup,
)
from src.evaluator import DimensionScore, EvalMode, Improvement, Priority
from src.evaluator.llm_schemas import FollowupLLMResponse


class TestBuildDimensionSummary:
    def test_formats_dimensions(self):
        state = {
            "dimension_scores": [
                DimensionScore(name="task", score=75, sub_criteria=[]),
                DimensionScore(name="context", score=50, sub_criteria=[]),
            ],
        }
        result = _build_dimension_summary(state)
        assert "Task: 75/100" in result
        assert "Context: 50/100" in result

    def test_empty_dimensions(self):
        state = {"dimension_scores": []}
        result = _build_dimension_summary(state)
        assert result == "No dimension scores available."

    def test_no_dimensions_key(self):
        state = {}
        result = _build_dimension_summary(state)
        assert result == "No dimension scores available."


class TestBuildImprovementsSummary:
    def test_formats_improvements(self):
        state = {
            "improvements": [
                Improvement(priority=Priority.CRITICAL, title="Add task", suggestion="Be specific"),
                Improvement(priority=Priority.LOW, title="Polish", suggestion="Minor tweaks"),
            ],
        }
        result = _build_improvements_summary(state)
        assert "[CRITICAL] Add task" in result
        assert "[LOW] Polish" in result

    def test_empty_improvements(self):
        state = {"improvements": []}
        result = _build_improvements_summary(state)
        assert result == "No improvements suggested."

    def test_no_improvements_key(self):
        state = {}
        result = _build_improvements_summary(state)
        assert result == "No improvements suggested."


class TestGetLatestUserMessage:
    def test_finds_human_message(self):
        state = {
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there"),
                HumanMessage(content="Explain the context score"),
            ],
        }
        assert _get_latest_user_message(state) == "Explain the context score"

    def test_no_human_messages(self):
        state = {"messages": [AIMessage(content="Hi")]}
        assert _get_latest_user_message(state) == ""

    def test_empty_messages(self):
        state = {"messages": []}
        assert _get_latest_user_message(state) == ""

    def test_no_messages_key(self):
        state = {}
        assert _get_latest_user_message(state) == ""


class TestMapFollowupResponse:
    def test_maps_full_response(self):
        resp = FollowupLLMResponse(
            intent="adjust_rewrite",
            response="Here is the adjusted version",
            new_rewrite="Better prompt",
        )
        result = _map_followup_response(resp)
        assert result["intent"] == "adjust_rewrite"
        assert result["new_rewrite"] == "Better prompt"
        assert result["new_prompt"] is None

    def test_maps_defaults(self):
        resp = FollowupLLMResponse()
        result = _map_followup_response(resp)
        assert result["intent"] == "explain"
        assert result["response"] == ""


class TestBuildStateUpdate:
    def test_explain_intent(self):
        result = {"intent": "explain", "response": "Details here", "new_prompt": None, "new_rewrite": None, "new_mode": None}
        state = {}
        update = _build_state_update(result, state)
        assert update["followup_action"] == "explain"
        assert update["current_step"] == "followup"
        assert len(update["messages"]) == 1
        assert "rewritten_prompt" not in update
        assert "input_text" not in update

    def test_adjust_rewrite_intent(self):
        result = {"intent": "adjust_rewrite", "response": "Adjusted", "new_prompt": None, "new_rewrite": "New rewrite", "new_mode": None}
        state = {}
        update = _build_state_update(result, state)
        assert update["followup_action"] == "adjust_rewrite"
        assert update["rewritten_prompt"] == "New rewrite"

    def test_adjust_rewrite_without_new_rewrite(self):
        result = {"intent": "adjust_rewrite", "response": "No changes needed", "new_prompt": None, "new_rewrite": None, "new_mode": None}
        state = {}
        update = _build_state_update(result, state)
        assert "rewritten_prompt" not in update

    def test_re_evaluate_intent(self):
        result = {"intent": "re_evaluate", "response": "Re-evaluating", "new_prompt": "Updated prompt", "new_rewrite": None, "new_mode": None}
        state = {}
        update = _build_state_update(result, state)
        assert update["followup_action"] == "re_evaluate"
        assert update["input_text"] == "Updated prompt"

    def test_mode_switch_to_system_prompt(self):
        result = {"intent": "mode_switch", "response": "Switching", "new_prompt": None, "new_rewrite": None, "new_mode": "system_prompt"}
        state = {}
        update = _build_state_update(result, state)
        assert update["followup_action"] == "mode_switch"
        assert update["mode"] == EvalMode.SYSTEM_PROMPT

    def test_mode_switch_to_prompt(self):
        result = {"intent": "mode_switch", "response": "Switching", "new_prompt": None, "new_rewrite": None, "new_mode": "prompt"}
        state = {}
        update = _build_state_update(result, state)
        assert update["mode"] == EvalMode.PROMPT

    def test_mode_switch_without_new_mode(self):
        result = {"intent": "mode_switch", "response": "Cannot switch", "new_prompt": None, "new_rewrite": None, "new_mode": None}
        state = {}
        update = _build_state_update(result, state)
        assert "mode" not in update


class TestHandleFollowup:
    @pytest.mark.asyncio
    async def test_handle_followup_explain(self):
        mock_response = FollowupLLMResponse(
            intent="explain",
            response="The task score reflects...",
        )

        with patch("src.agent.nodes.conversational.get_llm") as mock_llm, \
             patch("src.agent.nodes.conversational.invoke_structured", new_callable=AsyncMock) as mock_invoke:
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Write about dogs",
                "overall_score": 25,
                "grade": "Weak",
                "dimension_scores": [
                    DimensionScore(name="task", score=30, sub_criteria=[]),
                ],
                "improvements": [],
                "rewritten_prompt": None,
                "messages": [HumanMessage(content="Explain the task score")],
            }
            result = await handle_followup(state)

            assert result["followup_action"] == "explain"
            assert result["current_step"] == "followup"

    @pytest.mark.asyncio
    async def test_handle_followup_re_evaluate(self):
        mock_response = FollowupLLMResponse(
            intent="re_evaluate",
            response="Re-evaluating now",
            new_prompt="New prompt to evaluate",
        )

        with patch("src.agent.nodes.conversational.get_llm") as mock_llm, \
             patch("src.agent.nodes.conversational.invoke_structured", new_callable=AsyncMock) as mock_invoke:
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = mock_response

            state = {
                "input_text": "Write about dogs",
                "overall_score": 25,
                "grade": "Weak",
                "dimension_scores": [],
                "improvements": [],
                "rewritten_prompt": None,
                "messages": [HumanMessage(content="Re-evaluate: You are a vet...")],
            }
            result = await handle_followup(state)

            assert result["followup_action"] == "re_evaluate"
            assert result["input_text"] == "New prompt to evaluate"

    @pytest.mark.asyncio
    async def test_handle_followup_fallback_on_none(self):
        with patch("src.agent.nodes.conversational.get_llm") as mock_llm, \
             patch("src.agent.nodes.conversational.invoke_structured", new_callable=AsyncMock) as mock_invoke:
            mock_llm.return_value = MagicMock()
            mock_invoke.return_value = None

            state = {
                "input_text": "Write about dogs",
                "overall_score": 25,
                "grade": "Weak",
                "dimension_scores": [],
                "improvements": [],
                "rewritten_prompt": None,
                "messages": [HumanMessage(content="Tell me more")],
            }
            result = await handle_followup(state)

            assert result["followup_action"] == "explain"
            assert result["current_step"] == "followup"
