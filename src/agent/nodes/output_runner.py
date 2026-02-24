"""Output runner node — executes the user's prompt through an LLM multiple times."""

from __future__ import annotations

import asyncio
import logging

from langchain_core.messages import AIMessage, HumanMessage

from src.agent.state import AgentState
from src.evaluator.exceptions import format_fatal_error, is_fatal_llm_error
from src.utils.llm_factory import get_llm
from src.utils.structured_output import _extract_text_content

logger = logging.getLogger(__name__)


async def _run_n_times(llm: object, prompt_text: str, n: int) -> list[str]:
    """Execute a prompt N times concurrently and return all outputs.

    Handles partial failures gracefully — if some runs fail, the
    successful results are still returned.

    Args:
        llm: The LangChain chat model instance.
        prompt_text: The prompt text to execute.
        n: Number of concurrent executions.

    Returns:
        List of N output strings (errors are formatted as error messages).
    """
    async def _single_run() -> str:
        response = await llm.ainvoke([HumanMessage(content=prompt_text)])
        content = _extract_text_content(response)
        if not content:
            content = str(response.content) if response.content else "[Empty response]"
        return content

    results = await asyncio.gather(
        *[_single_run() for _ in range(n)], return_exceptions=True,
    )
    return [
        r if isinstance(r, str) else f"[Error: {r}]"
        for r in results
    ]


def _format_multi_output(outputs: list[str]) -> str:
    """Format multiple outputs into a single summary string.

    Args:
        outputs: List of output strings from N executions.

    Returns:
        Formatted string with run separators.
    """
    if len(outputs) == 1:
        return outputs[0]
    parts = []
    for i, output in enumerate(outputs, 1):
        parts.append(f"--- Run {i} ---\n{output}")
    return "\n\n".join(parts)


async def run_prompt_for_output(state: AgentState) -> dict:
    """Run the user's prompt through the configured LLM N times and capture outputs.

    Executes the original prompt concurrently ``execution_count`` times
    for reliability. The aggregated output is used for quality evaluation.
    LangSmith auto-traces via LANGCHAIN_TRACING_V2 env var.

    Args:
        state: Current agent state with input_text and execution_count.

    Returns:
        State update dict with llm_output, original_outputs,
        original_output_summary, and messages.
    """
    llm = get_llm(state.get("llm_provider"))
    input_text = state["input_text"]
    execution_count = state.get("execution_count") or 2

    try:
        outputs = await _run_n_times(llm, input_text, execution_count)

        # Check if all runs failed with fatal errors
        all_errors = all(o.startswith("[Error:") for o in outputs)
        if all_errors:
            # Check the first error for fatal condition
            content = outputs[0]
        else:
            content = _format_multi_output(outputs)

    except Exception as exc:
        logger.exception("LLM call failed in output runner: %s", exc)
        if is_fatal_llm_error(exc):
            return {
                "error_message": format_fatal_error(exc),
                "current_step": "error",
                "should_continue": False,
                "messages": [AIMessage(content=format_fatal_error(exc))],
            }
        outputs = [f"[Error: LLM call failed — {type(exc).__name__}: {exc}]"]
        content = outputs[0]

    return {
        "llm_output": content,
        "original_outputs": outputs,
        "original_output_summary": content,
        "current_step": "output_generated",
        "messages": [
            AIMessage(content=f"Output generated ({execution_count} runs) — now evaluating quality...")
        ],
    }
