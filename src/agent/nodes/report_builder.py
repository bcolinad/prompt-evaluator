"""Report builder node — assembles FullEvaluationReport from structure and/or output results."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage

from src.agent.state import AgentState
from src.db import get_session_factory
from src.embeddings.service import store_evaluation_embedding
from src.evaluator import EvalPhase, FullEvaluationReport, Improvement
from src.evaluator.exceptions import ReportBuildError

logger = logging.getLogger(__name__)


def _summarize_improvements(improvements: list[Improvement] | None) -> str | None:
    """Build a short text summary from improvement objects.

    Args:
        improvements: List of Improvement models, or None.

    Returns:
        Semicolon-separated summary of up to 5 improvements, or None if empty.
    """
    if not improvements:
        return None
    parts = [f"[{imp.priority.value}] {imp.suggestion[:100]}" for imp in improvements[:5]]
    return "; ".join(parts)


async def _store_embedding(state: AgentState) -> None:
    """Store evaluation embedding for self-learning (fire-and-forget).

    Args:
        state: Current agent state with evaluation data for embedding storage.
    """
    try:
        output_eval = state.get("output_evaluation")
        eval_result = state.get("evaluation_result")
        factory = get_session_factory()
        async with factory() as session:
            await store_evaluation_embedding(
                session=session,
                user_id=state.get("user_id"),
                evaluation_id=str(eval_result.id) if eval_result and hasattr(eval_result, "id") else None,
                input_text=state["input_text"],
                rewritten_prompt=state.get("rewritten_prompt"),
                overall_score=state.get("overall_score", 0),
                grade=state.get("grade", "Weak"),
                output_score=output_eval.overall_score if output_eval else None,
                improvements_summary=_summarize_improvements(state.get("improvements")),
                thread_id=state.get("thread_id"),
            )
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to store evaluation embedding: %s", exc)


async def build_report(state: AgentState) -> dict:
    """Assemble a FullEvaluationReport from available evaluation results.

    Merges structure findings (prefixed with [Structure/T.C.R.E.I.])
    and output findings (prefixed with [Output/LangSmith]) into
    combined_findings. Also stores the evaluation embedding for
    self-learning similarity search.

    Args:
        state: Current agent state with evaluation_result, output_evaluation, etc.

    Returns:
        State update dict with full_report and messages.
        On error, returns a minimal report with input_text only.
    """
    try:
        phase = state.get("eval_phase") or EvalPhase.STRUCTURE
        structure_result = state.get("evaluation_result")
        output_result = state.get("output_evaluation")

        combined_findings: list[str] = []

        # Collect structure findings
        if structure_result is not None:
            for dim in structure_result.dimensions:
                for sc in dim.sub_criteria:
                    prefix = "[Structure/T.C.R.E.I.]"
                    status = "Found" if sc.found else "Missing"
                    combined_findings.append(f"{prefix} {dim.name.title()} — {status}: {sc.detail}")

        # Collect output findings
        if output_result is not None:
            for finding in output_result.findings:
                combined_findings.append(f"[Output/LangSmith] {finding}")

        # Collect meta-evaluation findings
        meta_findings = state.get("meta_findings")
        if meta_findings:
            for finding in meta_findings:
                combined_findings.append(f"[Meta/Self-Evaluation] {finding}")

        rewritten_prompt = state.get("rewritten_prompt")
        meta_assessment = state.get("meta_assessment")

        # Always enhanced strategy
        strategy_used = "enhanced (CoT+ToT+Meta)"

        report = FullEvaluationReport(
            phase=phase,
            input_text=state["input_text"],
            structure_result=structure_result,
            output_result=output_result,
            combined_findings=combined_findings,
            rewritten_prompt=rewritten_prompt,
            meta_assessment=meta_assessment,
            strategy_used=strategy_used,
            optimized_output_result=state.get("optimized_output_evaluation"),
            execution_count=state.get("execution_count") or 2,
            original_outputs=state.get("original_outputs"),
            optimized_outputs=state.get("optimized_outputs"),
            cot_reasoning_trace=state.get("cot_reasoning_trace"),
            tot_branches_data=state.get("tot_branches_data"),
        )

        # Store embedding for self-learning (fire-and-forget)
        await _store_embedding(state)

        return {
            "full_report": report,
            "current_step": "report_complete",
            "should_continue": False,
            "messages": [
                AIMessage(content="✅ Evaluation report complete.")
            ],
        }

    except Exception as exc:
        logger.exception("build_report failed: %s", exc)
        domain_err = ReportBuildError(
            f"Report assembly failed: {exc}",
            context={"phase": str(state.get("eval_phase")), "original_error": str(exc)},
        )
        logger.error("Domain error: %s context=%s", domain_err, domain_err.context)
        actual_phase = state.get("eval_phase") or EvalPhase.STRUCTURE
        minimal_report = FullEvaluationReport(
            phase=actual_phase,
            input_text=state.get("input_text", ""),
        )
        return {
            "full_report": minimal_report,
            "current_step": "report_complete",
            "should_continue": False,
            "messages": [
                AIMessage(content=f"Report assembly failed: {type(exc).__name__}: {exc}. Partial report generated.")
            ],
        }
