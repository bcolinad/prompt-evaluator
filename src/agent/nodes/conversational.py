"""Conversational node — handles follow-up questions after evaluation."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.agent.state import AgentState
from src.evaluator import EvalMode
from src.evaluator.llm_schemas import FollowupLLMResponse
from src.prompts import FOLLOWUP_SYSTEM_PROMPT
from src.utils.llm_factory import get_llm
from src.utils.structured_output import invoke_structured

logger = logging.getLogger(__name__)


def _build_dimension_summary(state: AgentState) -> str:
    """Format dimension scores for the follow-up prompt context.

    Args:
        state: Current agent state with dimension_scores.

    Returns:
        Newline-separated list of dimension scores, or a "not available" message.
    """
    dimensions = state.get("dimension_scores", [])
    if not dimensions:
        return "No dimension scores available."
    return "\n".join(f"- {d.name.title()}: {d.score}/100" for d in dimensions)


def _build_improvements_summary(state: AgentState) -> str:
    """Format improvements list for the follow-up prompt context.

    Args:
        state: Current agent state with improvements list.

    Returns:
        Newline-separated list of improvements, or a "none suggested" message.
    """
    improvements = state.get("improvements", [])
    if not improvements:
        return "No improvements suggested."
    return "\n".join(f"- [{imp.priority.value}] {imp.title}: {imp.suggestion}" for imp in improvements)


def _get_latest_user_message(state: AgentState) -> str:
    """Extract the latest HumanMessage from conversation history.

    Args:
        state: Current agent state with messages list.

    Returns:
        Content of the most recent HumanMessage, or empty string.
    """
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def _map_followup_response(response: FollowupLLMResponse) -> dict:
    """Map a FollowupLLMResponse to a plain dict for state update.

    Args:
        response: Parsed LLM response with intent, response text, and optional fields.

    Returns:
        Dict with intent, response, new_prompt, new_rewrite, and new_mode.
    """
    return {
        "intent": response.intent,
        "response": response.response,
        "new_prompt": response.new_prompt,
        "new_rewrite": response.new_rewrite,
        "new_mode": response.new_mode,
    }


async def handle_followup(state: AgentState) -> dict:
    """Handle follow-up questions from the user after an evaluation.

    This node processes requests like:
    - "Explain the context score in more detail"
    - "Adjust the rewrite for a healthcare audience"
    - "Re-evaluate with this updated prompt: ..."
    - "Switch to system prompt mode"

    Args:
        state: Current agent state with messages, scores, and improvements.

    Returns:
        State update dict with followup_action and messages.
        On error, returns a generic error message to the user.
    """
    try:
        llm = get_llm(state.get("llm_provider"))

        dimension_summary = _build_dimension_summary(state)
        improvements_summary = _build_improvements_summary(state)
        rewritten_prompt = state.get("rewritten_prompt") or "No rewrite generated."
        user_message = _get_latest_user_message(state)

        system_content = FOLLOWUP_SYSTEM_PROMPT.format(
            overall_score=state.get("overall_score", 0),
            grade=state.get("grade", "Unknown"),
            dimension_summary=dimension_summary,
            improvements_summary=improvements_summary,
            rewritten_prompt=rewritten_prompt,
            original_prompt=state.get("input_text", ""),
        )

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_content),
            ("human", "{user_message}"),
        ])

        llm_result = await invoke_structured(
            llm, prompt, {"user_message": user_message}, FollowupLLMResponse,
        )

        if llm_result is not None:
            result = _map_followup_response(llm_result)
        else:
            logger.warning("All parsing attempts failed for follow-up — using text fallback")
            result = {
                "intent": "explain",
                "response": user_message,
                "new_prompt": None,
                "new_rewrite": None,
                "new_mode": None,
            }

        return _build_state_update(result, state)

    except Exception as exc:
        logger.exception("handle_followup failed: %s", exc)
        return {
            "current_step": "followup",
            "followup_action": "explain",
            "messages": [
                AIMessage(content="Sorry, I encountered an error processing your follow-up. Please try again.")
            ],
        }


def _build_state_update(result: dict, state: AgentState) -> dict:
    """Map follow-up intent to state changes.

    Args:
        result: Dict from ``_map_followup_response`` with intent and optional fields.
        state: Current agent state for reference.

    Returns:
        State update dict with appropriate fields based on the detected intent.
    """
    intent = result.get("intent", "explain")
    response_text = result.get("response", "I can help with that.")

    update: dict = {
        "current_step": "followup",
        "followup_action": intent,
        "messages": [AIMessage(content=response_text)],
    }

    if intent == "adjust_rewrite" and result.get("new_rewrite"):
        update["rewritten_prompt"] = result["new_rewrite"]

    elif intent == "re_evaluate" and result.get("new_prompt"):
        update["input_text"] = result["new_prompt"]

    elif intent == "mode_switch" and result.get("new_mode"):
        mode_str = result["new_mode"]
        if mode_str == "system_prompt":
            update["mode"] = EvalMode.SYSTEM_PROMPT
        else:
            update["mode"] = EvalMode.PROMPT

    return update
