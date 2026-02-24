"""Results display — audit reports and recommendations for the Chainlit UI."""

from __future__ import annotations

import logging
import tempfile
import uuid
from typing import Any

import chainlit as cl

from src.evaluator import FullEvaluationReport
from src.utils.report_generator import (
    _compute_composite_improvement,
    generate_audit_report,
    generate_similarity_report,
)

logger = logging.getLogger(__name__)


async def _send_results(final_state: dict[str, Any]) -> None:
    """Generate professional audit report, attach as file, send summary message.

    Args:
        final_state: Accumulated state dict from the LangGraph evaluation run.
    """
    report: FullEvaluationReport | None = final_state.get("full_report")
    if not report:
        await cl.Message(  # type: ignore[no-untyped-call]
            content="Could not complete the evaluation. Please try again."
        ).send()
        return

    # Build short, unique filename using UUID4 prefix
    short_id = uuid.uuid4().hex[:8]
    report_filename = f"audit-{short_id}.html"

    # Generate HTML audit report via report generator
    html_content = generate_audit_report(report)
    with tempfile.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(html_content)
        temp_path = f.name

    # Compute headline numbers
    struct_score = (
        report.structure_result.overall_score if report.structure_result else 0
    )
    struct_grade = (
        report.structure_result.grade.value if report.structure_result else "N/A"
    )
    output_pct = (
        int(report.output_result.overall_score * 100)
        if report.output_result
        else 0
    )

    # Compute optimized output score
    optimized_pct = (
        int(report.optimized_output_result.overall_score * 100)
        if report.optimized_output_result
        else 0
    )

    # Composite improvement from all four engines
    tot_confidence = None
    if report.tot_branches_data and report.tot_branches_data.branches:
        idx = report.tot_branches_data.selected_branch_index
        if 0 <= idx < len(report.tot_branches_data.branches):
            tot_confidence = report.tot_branches_data.branches[idx].confidence

    meta_confidence = (
        report.meta_assessment.overall_confidence if report.meta_assessment else None
    )

    composite = _compute_composite_improvement(
        struct_score=struct_score,
        output_score=output_pct,
        opt_output_score=optimized_pct,
        meta_confidence=meta_confidence,
        tot_branch_confidence=tot_confidence,
    )
    delta = composite["composite_pct"]

    # Build concise markdown summary for the chat
    summary_lines = [
        f"## Audit Complete \u2014 **{struct_grade}**",
        "",
        f"**Structure:** {struct_score}% | **Original Output:** {output_pct}%",
    ]

    if report.optimized_output_result:
        delta_sign = "+" if delta >= 0 else ""
        summary_lines.append(
            f"**Optimized Output:** {optimized_pct}% | **Composite Improvement:** {delta_sign}{delta}%"
        )
        summary_lines.append(
            f"  - T.C.R.E.I. Gap: {composite['structural_signal_pct']}% | "
            f"Output Delta: {composite['output_delta_sign']}{composite['output_delta']}% | "
            f"Meta: {composite['meta_confidence_pct']}% | "
            f"ToT: {composite['tot_confidence_pct']}%"
        )

    # Always show strategy and meta-evaluation confidence
    summary_lines.append(f"**Strategy:** {report.strategy_used}")
    if report.meta_assessment:
        confidence = int(report.meta_assessment.overall_confidence * 100)
        summary_lines.append(f"**Meta-Evaluation Confidence:** {confidence}%")

    if report.execution_count > 1:
        summary_lines.append(f"**Execution Count:** {report.execution_count}x per prompt")

    summary_lines.append("")

    # Dimension quick view
    if report.structure_result:
        for dim in report.structure_result.dimensions:
            icon = "\u2705" if dim.score >= 60 else "\u26a0\ufe0f" if dim.score >= 40 else "\u274c"
            summary_lines.append(f"- {icon} **{dim.name.title()}** {dim.score}%")
        summary_lines.append("")

    # Top improvements (full details, no truncation)
    if report.structure_result and report.structure_result.improvements:
        summary_lines.append("**Top improvements:**")
        for imp in report.structure_result.improvements:
            summary_lines.append(
                f"- **[{imp.priority.value}]** {imp.suggestion}"
            )
        summary_lines.append("")

    summary_lines.append(
        f"Open the attached **{report_filename}** for the full interactive professional audit dashboard."
    )

    elements = [
        cl.File(name=report_filename, path=temp_path, display="inline")
    ]

    await cl.Message(  # type: ignore[no-untyped-call]
        content="\n".join(summary_lines),
        elements=elements,
    ).send()


async def _send_recommendations(final_state: dict[str, Any]) -> None:
    """Show similar past evaluations as a recommendations panel.

    For each evaluation that has a ``rewritten_prompt``, generates a
    downloadable HTML report and attaches it as a ``cl.File`` element.

    Args:
        final_state: Accumulated state dict that may contain similar_evaluations.
    """
    similar = final_state.get("similar_evaluations", [])
    if not similar:
        return

    lines = ["### Similar Past Evaluations\n"]
    elements: list[cl.File] = []

    for i, eval_data in enumerate(similar[:3], 1):
        score = eval_data["overall_score"]
        grade = eval_data["grade"]
        similarity = int((1 - eval_data["distance"]) * 100)
        prompt_preview = eval_data["input_text"][:100] + "..."

        if eval_data.get("rewritten_prompt"):
            short_id = uuid.uuid4().hex[:8]
            report_filename = f"past-eval-{i}-{short_id}.html"
            html_content = generate_similarity_report(eval_data)
            with tempfile.NamedTemporaryFile(
                suffix=".html", delete=False, mode="w", encoding="utf-8"
            ) as f:
                f.write(html_content)
                temp_path = f.name
            elements.append(
                cl.File(name=report_filename, path=temp_path, display="inline")
            )
            lines.append(
                f"**{i}. {grade}** ({score}/100) \u2014 {similarity}% similar\n"
                f"> {prompt_preview}\n"
                f"See attached **{report_filename}** for the optimized prompt.\n"
            )
        else:
            lines.append(
                f"**{i}. {grade}** ({score}/100) \u2014 {similarity}% similar\n"
                f"> {prompt_preview}\n"
            )

    msg_kwargs: dict[str, Any] = {"content": "\n".join(lines)}
    if elements:
        msg_kwargs["elements"] = elements

    await cl.Message(**msg_kwargs).send()  # type: ignore[no-untyped-call]
