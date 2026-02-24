"""Optimized prompt runner node — executes the rewritten prompt through an LLM multiple times."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage

from src.agent.nodes.output_runner import _format_multi_output, _run_n_times
from src.agent.state import AgentState
from src.evaluator.exceptions import format_fatal_error, is_fatal_llm_error
from src.utils.llm_factory import get_llm

logger = logging.getLogger(__name__)


async def run_optimized_prompt(state: AgentState) -> dict:
    """Run the rewritten/optimized prompt through the LLM N times.

    If no rewritten prompt is available, skips gracefully and returns
    empty optimized outputs so the pipeline can continue.

    Args:
        state: Current agent state with rewritten_prompt and execution_count.

    Returns:
        State update dict with optimized_outputs, optimized_output_summary,
        and messages.
    """
    rewritten_prompt = state.get("rewritten_prompt")
    if not rewritten_prompt:
        logger.info("No rewritten prompt available — skipping optimized runner")
        return {
            "optimized_outputs": None,
            "optimized_output_summary": None,
            "current_step": "optimized_output_generated",
            "messages": [
                AIMessage(content="No optimized prompt to execute — skipping.")
            ],
        }

    llm = get_llm(state.get("llm_provider"))
    execution_count = state.get("execution_count") or 2

    try:
        outputs = await _run_n_times(llm, rewritten_prompt, execution_count)
        summary = _format_multi_output(outputs)
    except Exception as exc:
        logger.exception("LLM call failed in optimized runner: %s", exc)
        if is_fatal_llm_error(exc):
            return {
                "error_message": format_fatal_error(exc),
                "current_step": "error",
                "should_continue": False,
                "messages": [AIMessage(content=format_fatal_error(exc))],
            }
        outputs = [f"[Error: LLM call failed — {type(exc).__name__}: {exc}]"]
        summary = outputs[0]

    return {
        "optimized_outputs": outputs,
        "optimized_output_summary": summary,
        "current_step": "optimized_output_generated",
        "messages": [
            AIMessage(content=f"Optimized prompt executed ({execution_count} runs) — evaluating quality...")
        ],
    }
