"""Evaluation pipeline runner with real-time progress display."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import chainlit as cl
from langchain_core.messages import HumanMessage

from src.agent.graph import get_graph
from src.evaluator import EvalMode, EvalPhase, TaskType
from src.evaluator.strategies import get_default_strategy
from src.ui.results_display import _send_recommendations, _send_results

logger = logging.getLogger(__name__)

# Maps graph node names -> (display label, default detail, progress weight)
# Progress weight indicates relative time each step takes (for % estimation)
NODE_STEP_MAP: dict[str, tuple[str, str, int]] = {
    "route_input": ("Routing Input", "Detecting evaluation mode and phase", 3),
    "analyze_prompt": ("Analyzing Dimensions (CoT)", "Step-by-step T.C.R.E.I. reasoning via Chain-of-Thought", 15),
    "analyze_system_prompt": (
        "Analyzing System Prompt (CoT)",
        "Step-by-step system prompt analysis via Chain-of-Thought",
        15,
    ),
    "score_prompt": ("Computing Scores", "Calculating weighted scores per dimension and assigning grade", 10),
    "generate_improvements": (
        "Generating Improvements (ToT)",
        "Multi-branch Tree-of-Thought improvement exploration",
        15,
    ),
    "run_prompt_for_output": (
        "Running Original Prompt",
        "Executing prompt via LLM (multi-execution for reliability)",
        12,
    ),
    "evaluate_output": ("Evaluating Original Output", "LLM-as-Judge scoring across 5 quality dimensions", 10),
    "run_optimized_prompt": ("Running Optimized Prompt", "Executing optimized prompt via LLM (multi-execution)", 12),
    "evaluate_optimized_output": (
        "Evaluating Optimized Output",
        "LLM-as-Judge scoring optimized prompt output quality",
        8,
    ),
    "meta_evaluate": ("Meta-Evaluating", "Self-reflection pass assessing evaluation accuracy and completeness", 8),
    "build_report": ("Building Report", "Assembling final audit report with CoT, ToT, comparison sections", 7),
}


async def _run_evaluation(user_input: str, mode: EvalMode) -> None:
    """Run the LangGraph full evaluation with real-time step progress."""
    user_id: str = cl.user_session.get("user_id", "anonymous")  # type: ignore[no-untyped-call]
    logger.info("Starting evaluation for user=%s mode=%s input_length=%d", user_id, mode.value, len(user_input))

    task_type: TaskType = cl.user_session.get("task_type", TaskType.GENERAL)  # type: ignore[no-untyped-call]
    llm_provider: str = cl.user_session.get("llm_provider", "google")  # type: ignore[no-untyped-call]

    # Always use enhanced strategy (CoT+ToT+Meta)
    strategy_config = get_default_strategy()

    # Read execution count from session
    execution_count: int = cl.user_session.get("execution_count", 2)  # type: ignore[no-untyped-call]

    # Retrieve document context if documents have been uploaded
    # Prefer full document content (stored in session), fall back to RAG
    document_context: str | None = None
    document_ids: list[str] = cl.user_session.get("document_ids", [])  # type: ignore[no-untyped-call]
    document_summary: str | None = None
    if document_ids:
        doc_full_contexts: list[str] = cl.user_session.get("document_full_contexts", [])  # type: ignore[no-untyped-call]
        if doc_full_contexts:
            document_context = "\n\n---\n\n".join(doc_full_contexts)
        else:
            # Try to retrieve full document text from DB first (zero information loss)
            document_context = await _retrieve_full_document_text_for_eval(document_ids)
            if not document_context:
                # Fall back to RAG retrieval
                document_context = await _retrieve_document_context_for_eval(user_input, user_id, document_ids)
        if document_context:
            document_summary = f"Using context from {len(document_ids)} uploaded document(s)"

    initial_state: dict[str, Any] = {
        "messages": [HumanMessage(content=user_input)],
        "input_text": user_input,
        "mode": mode,
        "eval_phase": EvalPhase.FULL,
        "expected_outcome": None,
        "session_id": cl.user_session.get("id", "default"),  # type: ignore[no-untyped-call]
        "thread_id": cl.context.session.thread_id,
        "user_id": user_id,
        "task_type": task_type,
        "llm_provider": llm_provider,
        "strategy": strategy_config,
        "execution_count": execution_count,
        "should_continue": False,
        "document_context": document_context,
        "document_ids": document_ids if document_ids else None,
        "document_summary": document_summary,
    }

    final_state: dict[str, Any] = {
        "user_id": user_id,
        "session_id": initial_state["session_id"],
    }
    start_time = time.monotonic()
    last_event_time = start_time  # Track time between events for step duration
    completed_weight = 0
    steps_completed = 0

    # Send initial progress message that we'll update
    progress_msg = cl.Message(content="**Starting evaluation...**")
    await progress_msg.send()  # type: ignore[no-untyped-call]

    try:
        async for event in get_graph().astream(  # type: ignore[attr-defined]
            initial_state, stream_mode="updates"
        ):
            for node_name, state_update in event.items():
                now = time.monotonic()
                step_duration = now - last_event_time  # Time the node actually ran
                last_event_time = now

                label, detail, weight = NODE_STEP_MAP.get(node_name, (node_name, "Processing...", 5))
                steps_completed += 1
                completed_weight += weight

                # Calculate progress percentage based on weights
                total_weight = sum(w for _, _, w in NODE_STEP_MAP.values())
                progress_pct = min(int((completed_weight / total_weight) * 100), 100)
                elapsed = now - start_time

                step_output = _extract_step_summary(node_name, state_update)

                # Show detailed step in the thinking panel
                async with cl.Step(name=f"[{progress_pct}%] {label}") as step:
                    step.output = (
                        f"{step_output or detail}\n\n*Step took {step_duration:.1f}s | Total elapsed: {elapsed:.1f}s*"
                    )

                # Update progress message in chat
                bar = _progress_bar(progress_pct)
                progress_msg.content = (
                    f"**Evaluation in progress** {bar} **{progress_pct}%**\n\n"
                    f"Completed: **{label}** ({step_duration:.1f}s) | Total: {elapsed:.1f}s"
                )
                await progress_msg.update()  # type: ignore[no-untyped-call]

                logger.info(
                    "[%d%%] %s took %.1fs (total: %.1fs)",
                    progress_pct,
                    node_name,
                    step_duration,
                    elapsed,
                )

                if isinstance(state_update, dict):
                    final_state.update(state_update)

        # Check for fatal error — abort and show to user
        total_elapsed = time.monotonic() - start_time
        error_msg = final_state.get("error_message")
        if error_msg:
            logger.error(
                "Evaluation aborted after %d steps in %.1fs due to fatal error",
                steps_completed,
                total_elapsed,
            )
            progress_msg.content = (
                f"**Evaluation stopped** {_progress_bar(0)} **Error**\n\n"
                f"Aborted after **{steps_completed} steps** in **{total_elapsed:.1f}s**"
            )
            await progress_msg.update()  # type: ignore[no-untyped-call]
            await cl.Message(content=error_msg).send()  # type: ignore[no-untyped-call]
            return

        # Final progress update
        logger.info(
            "Evaluation complete: %d steps in %.1fs, score=%s grade=%s",
            steps_completed,
            total_elapsed,
            final_state.get("overall_score", "N/A"),
            final_state.get("grade", "N/A"),
        )
        progress_msg.content = (
            f"**Evaluation complete** {_progress_bar(100)} **100%**\n\n"
            f"Completed **{steps_completed} steps** in **{total_elapsed:.1f}s**"
        )
        await progress_msg.update()  # type: ignore[no-untyped-call]

        await _send_results(final_state)
        await _send_recommendations(final_state)

    except Exception as e:
        logger.exception("Evaluation failed: %s", e)
        await cl.Message(  # type: ignore[no-untyped-call]
            content=f"Error during evaluation: {e}"
        ).send()


def _progress_bar(pct: int) -> str:
    """Build a text-based progress bar.

    Args:
        pct: Percentage complete (0-100).

    Returns:
        Bracketed progress bar string like ``[====------]``.
    """
    filled = pct // 10
    empty = 10 - filled
    return f"[{'=' * filled}{'-' * empty}]"


def _extract_route_summary(su: dict[str, Any]) -> str | None:
    m = su.get("mode")
    phase = su.get("eval_phase")
    parts: list[str] = []
    if m:
        parts.append(f"Mode: **{m.value.replace('_', ' ').title()}**")
    if phase:
        phase_val = phase.value if hasattr(phase, "value") else str(phase)
        parts.append(f"Phase: **{phase_val.title()}**")
    return " | ".join(parts) if parts else None


def _extract_analysis_summary(su: dict[str, Any]) -> str | None:
    dims = su.get("dimension_scores")
    if dims:
        dim_parts = [f"{d.name.title()}: {d.score}%" for d in dims]
        return "Dimension scores: " + " | ".join(dim_parts)
    return None


def _extract_score_summary(su: dict[str, Any]) -> str | None:
    score = su.get("overall_score")
    grade = su.get("grade")
    if score is not None and grade:
        return f"Overall score: **{score}/100** \u2014 {grade}"
    return None


def _extract_run_output_summary(su: dict[str, Any]) -> str | None:
    outputs = su.get("original_outputs")
    if outputs:
        return f"Generated **{len(outputs)}** output(s) ({sum(len(o) for o in outputs)} total chars)"
    output = su.get("llm_output")
    if output:
        return f"Generated output ({len(output)} chars)"
    return None


def _extract_output_eval_summary(su: dict[str, Any]) -> str | None:
    oe = su.get("output_evaluation")
    if oe and hasattr(oe, "overall_score"):
        return f"Original output quality: **{oe.overall_score:.2f}/1.0** \u2014 {oe.grade.value}"
    return None


def _extract_improvements_summary(su: dict[str, Any]) -> str | None:
    imps = su.get("improvements")
    rewritten = su.get("rewritten_prompt")
    tot = su.get("tot_branches_data")
    parts: list[str] = []
    if imps:
        parts.append(f"**{len(imps)}** improvement suggestions")
    if rewritten:
        parts.append("optimized prompt generated")
    if tot:
        parts.append(f"ToT: {len(tot.branches)} branches explored")
    return "Generated " + " + ".join(parts) if parts else None


def _extract_run_optimized_summary(su: dict[str, Any]) -> str | None:
    outputs = su.get("optimized_outputs")
    if outputs:
        return f"Optimized prompt executed: **{len(outputs)}** output(s) ({sum(len(o) for o in outputs)} total chars)"
    return None


def _extract_eval_optimized_summary(su: dict[str, Any]) -> str | None:
    oe = su.get("optimized_output_evaluation")
    if oe and hasattr(oe, "overall_score"):
        return f"Optimized output quality: **{oe.overall_score:.2f}/1.0** \u2014 {oe.grade.value}"
    return None


def _extract_meta_evaluate_summary(su: dict[str, Any]) -> str | None:
    meta = su.get("meta_assessment")
    findings = su.get("meta_findings")
    parts: list[str] = []
    if meta:
        parts.append(f"Confidence: **{meta.overall_confidence:.0%}**")
    if findings:
        parts.append(f"**{len(findings)}** meta-findings")
    return "Meta-evaluation: " + " | ".join(parts) if parts else None


def _extract_report_summary(su: dict[str, Any]) -> str | None:
    report = su.get("full_report")
    if report:
        return "Full audit report assembled with structure + output + comparison analysis"
    return "Report assembled"


_STEP_EXTRACTORS: dict[str, Callable[[dict[str, Any]], str | None]] = {
    "route_input": _extract_route_summary,
    "analyze_prompt": _extract_analysis_summary,
    "analyze_system_prompt": _extract_analysis_summary,
    "score_prompt": _extract_score_summary,
    "run_prompt_for_output": _extract_run_output_summary,
    "evaluate_output": _extract_output_eval_summary,
    "generate_improvements": _extract_improvements_summary,
    "run_optimized_prompt": _extract_run_optimized_summary,
    "evaluate_optimized_output": _extract_eval_optimized_summary,
    "meta_evaluate": _extract_meta_evaluate_summary,
    "build_report": _extract_report_summary,
}


def _extract_step_summary(node_name: str, state_update: dict[str, Any]) -> str | None:
    """Extract a detailed summary from a node's state update.

    Args:
        node_name: The LangGraph node name that just completed.
        state_update: The dict of state changes produced by the node.

    Returns:
        Human-readable summary string, or None if no summary available.
    """
    if not isinstance(state_update, dict):
        return None
    extractor = _STEP_EXTRACTORS.get(node_name)
    return extractor(state_update) if extractor else None


async def _retrieve_document_context_for_eval(
    query: str,
    user_id: str,
    document_ids: list[str],
) -> str | None:
    """Retrieve document context for evaluation mode via RAG.

    Args:
        query: The user's prompt to find relevant document chunks for.
        user_id: Authenticated user identifier.
        document_ids: List of document ID strings to search within.

    Returns:
        Formatted document context string, or None.
    """
    from src.db import get_session_factory
    from src.documents.retriever import retrieve_document_context

    try:
        thread_id: str | None = cl.context.session.thread_id
        factory = get_session_factory()
        async with factory() as session:
            context = await retrieve_document_context(
                session,
                query=query,
                user_id=user_id,
                thread_id=thread_id,
                document_ids=document_ids,
            )
            return context if context else None
    except Exception as exc:
        logger.warning("Document context retrieval for evaluation failed: %s", exc)
        return None


async def _retrieve_full_document_text_for_eval(
    document_ids: list[str],
) -> str | None:
    """Retrieve full document text from the database for evaluation mode.

    This retrieves the complete raw text stored in the documents table,
    ensuring zero information loss. Falls back to None if unavailable.

    Args:
        document_ids: List of document ID strings.

    Returns:
        Full document text with metadata, or None.
    """
    from src.db import get_session_factory
    from src.documents.retriever import retrieve_full_document_text

    try:
        factory = get_session_factory()
        async with factory() as session:
            text = await retrieve_full_document_text(session, document_ids)
            return text if text else None
    except Exception as exc:
        logger.warning("Full document text retrieval for evaluation failed: %s", exc)
        return None
