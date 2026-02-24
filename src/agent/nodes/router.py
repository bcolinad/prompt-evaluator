"""Router node — determines evaluation mode from user input."""

from __future__ import annotations

import logging
import re

from langchain_core.messages import AIMessage

from src.agent.state import AgentState
from src.evaluator import EvalMode

logger = logging.getLogger(__name__)


def route_input(state: AgentState) -> dict:
    """Detect whether the user wants prompt evaluation or system prompt evaluation.

    Heuristics:
    - If the user explicitly mentions 'system prompt', route to system prompt eval.
    - If expected_outcome is provided, route to system prompt eval.
    - Otherwise, default to prompt evaluation.

    The eval_phase is preserved from state (set by the Chainlit app).

    Args:
        state: Current agent state with input_text.

    Returns:
        State update dict with mode, prompt_type, and messages.
        On error, defaults to EvalMode.PROMPT.
    """
    try:
        input_text = state["input_text"].lower()
        expected_outcome = state.get("expected_outcome")

        system_prompt_signals = [
            "system prompt",
            "system message",
            "system instruction",
            "evaluate my system",
            "evaluate this system",
        ]

        is_system_prompt = expected_outcome is not None or any(signal in input_text for signal in system_prompt_signals)

        mode = EvalMode.SYSTEM_PROMPT if is_system_prompt else EvalMode.PROMPT

        # Detect whether the prompt is a continuation or initial/standalone prompt
        prompt_type = _detect_prompt_type(input_text)

        update: dict = {
            "mode": mode,
            "prompt_type": prompt_type,
            "current_step": "routing",
            "messages": [
                AIMessage(content=f"🔀 Detected mode: **{mode.value.replace('_', ' ').title()}** Evaluation")
            ],
        }

        # Preserve eval_phase from state
        eval_phase = state.get("eval_phase")
        if eval_phase is not None:
            update["eval_phase"] = eval_phase

        return update

    except Exception as exc:
        logger.exception("route_input failed: %s", exc)
        return {
            "mode": EvalMode.PROMPT,
            "prompt_type": "initial",
            "current_step": "routing",
            "messages": [
                AIMessage(content="🔀 Detected mode: **Prompt** Evaluation")
            ],
        }


# Signals that indicate the prompt continues or references a prior conversation
_CONTINUATION_SIGNALS: list[str] = [
    "as discussed", "as mentioned", "based on the above", "from earlier",
    "your previous response", "the code you wrote", "your output",
    "the results above", "what you said", "the example above",
    "now make", "now add", "now change", "now create", "now update",
    "can you also", "also add", "also change", "also include",
    "follow up", "following up", "continuing from",
    "based on our", "based on your", "from our last",
]

# Short prompts containing these anaphoric words likely reference prior context.
# Single words use regex word-boundary matching; multi-word phrases use substring matching.
_ANAPHORIC_SINGLE_WORDS: list[str] = [
    "it", "this", "that", "these", "those",
]
_ANAPHORIC_PHRASES: list[str] = [
    "the code", "the output",
]

# Pre-compiled pattern for single-word anaphoric references (whole-word match)
_ANAPHORIC_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in _ANAPHORIC_SINGLE_WORDS) + r")\b",
    re.IGNORECASE,
)

_SHORT_PROMPT_THRESHOLD = 30


def _detect_prompt_type(input_text: str) -> str:
    """Classify a prompt as 'initial' (standalone) or 'continuation' (references prior context).

    Uses two heuristics:
    1. Explicit continuation signal phrases (e.g. "now add", "based on the above").
    2. Short prompts (<= 30 words) with anaphoric references (e.g. "make it shorter").

    Args:
        input_text: The raw user input text.

    Returns:
        Either ``"initial"`` or ``"continuation"``.
    """
    lowered = input_text.lower()

    has_continuation_signal = any(
        signal in lowered for signal in _CONTINUATION_SIGNALS
    )
    if has_continuation_signal:
        return "continuation"

    word_count = len(input_text.split())
    has_anaphoric_ref = (
        bool(_ANAPHORIC_PATTERN.search(input_text))
        or any(phrase in lowered for phrase in _ANAPHORIC_PHRASES)
    )
    if word_count <= _SHORT_PROMPT_THRESHOLD and has_anaphoric_ref:
        return "continuation"

    return "initial"
