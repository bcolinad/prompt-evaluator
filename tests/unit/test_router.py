"""Unit tests for the router node."""


from src.agent.nodes.router import route_input
from src.evaluator import EvalMode


class TestRouteInput:
    def test_routes_to_prompt_eval_by_default(self):
        state = {
            "input_text": "Write a blog post about dogs",
            "expected_outcome": None,
        }
        result = route_input(state)
        assert result["mode"] == EvalMode.PROMPT

    def test_routes_to_system_prompt_eval_with_keyword(self):
        state = {
            "input_text": "Evaluate my system prompt: You are a helpful assistant...",
            "expected_outcome": None,
        }
        result = route_input(state)
        assert result["mode"] == EvalMode.SYSTEM_PROMPT

    def test_routes_to_system_prompt_eval_with_expected_outcome(self):
        state = {
            "input_text": "You are a medical transcription assistant...",
            "expected_outcome": "Structured SOAP notes",
        }
        result = route_input(state)
        assert result["mode"] == EvalMode.SYSTEM_PROMPT

    def test_case_insensitive_detection(self):
        state = {
            "input_text": "Please evaluate this SYSTEM PROMPT for me",
            "expected_outcome": None,
        }
        result = route_input(state)
        assert result["mode"] == EvalMode.SYSTEM_PROMPT

    def test_returns_messages(self):
        state = {"input_text": "test", "expected_outcome": None}
        result = route_input(state)
        assert "messages" in result
        assert len(result["messages"]) > 0
