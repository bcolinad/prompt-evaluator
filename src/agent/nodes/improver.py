"""Improver node — generates actionable improvements and a rewritten prompt."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.agent.state import AgentState
from src.evaluator import (
    EvaluationResult,
    Grade,
    Improvement,
    OutputEvaluationResult,
    Priority,
    ToTBranchAuditEntry,
    ToTBranchesAuditData,
)
from src.evaluator.exceptions import ImprovementError, format_fatal_error, is_fatal_llm_error
from src.evaluator.llm_schemas import (
    ImprovementsLLMResponse,
    ToTBranchesLLMResponse,
    ToTSelectionLLMResponse,
)
from src.prompts import IMPROVEMENT_SYSTEM_PROMPT, PROMPT_TYPE_CONTINUATION, PROMPT_TYPE_INITIAL
from src.prompts.registry import get_prompts_for_task_type
from src.prompts.strategies.tot import TOT_BRANCH_GENERATION_PROMPT, TOT_BRANCH_SELECTION_PROMPT
from src.rag.knowledge_store import retrieve_context
from src.utils.llm_factory import get_llm
from src.utils.structured_output import invoke_plain_text, invoke_structured

logger = logging.getLogger(__name__)

# Prompts larger than this (chars) use the two-phase strategy to avoid
# LLM output truncation when generating the rewritten prompt inside JSON.
_LARGE_PROMPT_THRESHOLD = 8000


def _format_historical_improvements(similar_evals: list[dict]) -> str:
    """Format effective improvements from similar past evaluations.

    Args:
        similar_evals: List of similar evaluation dicts from embedding search.

    Returns:
        Markdown-formatted string, or empty string if no improvements found.
    """
    lines = ["## Effective Improvements from Similar Prompts"]
    for i, ev in enumerate(similar_evals[:3], 1):
        if ev.get("improvements_summary"):
            score = ev["overall_score"]
            grade = ev["grade"]
            lines.append(f"{i}. ({score}/100 - {grade}): {ev['improvements_summary'][:300]}")
            if ev.get("rewritten_prompt"):
                lines.append(f"   Rewritten: {ev['rewritten_prompt'][:200]}...")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


async def _generate_tot_improvements(
    llm: object,
    input_text: str,
    analysis_summary: str,
    overall_score: int,
    grade: str,
    output_quality_section: str,
    num_branches: int = 3,
) -> dict | None:
    """Generate improvements using Tree-of-Thought branching.

    Phase 1: Generate N distinct improvement branches.
    Phase 2: Select or synthesize the best branch.

    Args:
        llm: The LangChain chat model instance.
        input_text: The original prompt text.
        analysis_summary: Formatted dimension scores summary.
        overall_score: The overall evaluation score.
        grade: The evaluation grade string.
        output_quality_section: Formatted output quality summary.
        num_branches: Number of improvement branches to generate.

    Returns:
        Dict with ``improvements`` and ``rewritten_prompt``, or None on failure.
    """
    try:
        # Phase 1: Generate branches
        branch_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=TOT_BRANCH_GENERATION_PROMPT.format(
                num_branches=num_branches,
                input_text=input_text,
                analysis_summary=analysis_summary,
                overall_score=overall_score,
                grade=grade,
                output_quality_section=output_quality_section,
            )),
            ("human", "Generate {num_branches} distinct improvement branches for the prompt above."),
        ])

        branches_result = await invoke_structured(
            llm, branch_prompt, {"num_branches": num_branches}, ToTBranchesLLMResponse,
        )

        if branches_result is None or not branches_result.branches:
            logger.warning("ToT branch generation returned no branches — falling back to standard")
            return None

        # Format branches for selection prompt
        branches_text_parts = []
        for i, branch in enumerate(branches_result.branches):
            imp_text = "\n".join(
                f"  - [{imp.priority}] {imp.title}: {imp.suggestion}"
                for imp in branch.improvements
            )
            branches_text_parts.append(
                f"### Branch {i + 1} (confidence: {branch.confidence:.2f})\n"
                f"**Approach:** {branch.approach}\n"
                f"**Improvements:**\n{imp_text}\n"
                f"**Rewritten prompt:**\n```\n{branch.rewritten_prompt}\n```"
            )
        branches_text = "\n\n".join(branches_text_parts)

        # Phase 2: Select best branch
        selection_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=TOT_BRANCH_SELECTION_PROMPT.format(
                num_branches=len(branches_result.branches),
                input_text=input_text,
                overall_score=overall_score,
                grade=grade,
                branches_text=branches_text,
            )),
            ("human", "Select the best branch or synthesize the strongest elements."),
        ])

        selection_result = await invoke_structured(
            llm, selection_prompt, {}, ToTSelectionLLMResponse,
        )

        # Build audit trail from branches
        audit_entries = [
            ToTBranchAuditEntry(
                approach=branch.approach,
                improvements_count=len(branch.improvements),
                rewritten_prompt_preview=(branch.rewritten_prompt or "")[:200],
                confidence=branch.confidence,
            )
            for branch in branches_result.branches
        ]

        if selection_result is None:
            logger.warning("ToT branch selection failed — using highest-confidence branch")
            best_idx = max(range(len(branches_result.branches)), key=lambda i: branches_result.branches[i].confidence)
            best = branches_result.branches[best_idx]
            audit_data = ToTBranchesAuditData(
                branches=audit_entries,
                selected_branch_index=best_idx,
                selection_rationale="Automatic: highest confidence branch selected (selection LLM call failed)",
                synthesized=False,
            )
            return {
                "improvements": [
                    Improvement(
                        priority=Priority(imp.priority),
                        title=imp.title,
                        suggestion=imp.suggestion,
                    )
                    for imp in best.improvements
                ],
                "rewritten_prompt": best.rewritten_prompt or None,
                "tot_branches_data": audit_data,
            }

        # Use synthesized prompt if available, otherwise use selected branch
        rewritten = selection_result.synthesized_prompt
        idx = selection_result.selected_branch_index
        if idx is None:
            # LLM returned null for index — use highest-confidence branch
            idx = max(range(len(branches_result.branches)), key=lambda i: branches_result.branches[i].confidence)
            logger.info("ToT selection returned null index — using highest-confidence branch %d", idx)
        if 0 <= idx < len(branches_result.branches):
            selected_branch = branches_result.branches[idx]
            improvements = [
                Improvement(
                    priority=Priority(imp.priority),
                    title=imp.title,
                    suggestion=imp.suggestion,
                )
                for imp in selected_branch.improvements
            ]
            # Fall back to the selected branch's rewritten prompt when
            # the synthesis step returned an empty/missing prompt.
            if not rewritten and selected_branch.rewritten_prompt:
                rewritten = selected_branch.rewritten_prompt
                logger.info("ToT synthesized_prompt empty — using selected branch %d rewritten prompt", idx)
        else:
            improvements = []

        audit_data = ToTBranchesAuditData(
            branches=audit_entries,
            selected_branch_index=idx,
            selection_rationale=selection_result.rationale if hasattr(selection_result, "rationale") else "LLM-selected best branch",
            synthesized=bool(selection_result.synthesized_prompt),
        )

        return {
            "improvements": improvements,
            "rewritten_prompt": rewritten or None,
            "tot_branches_data": audit_data,
        }

    except Exception as exc:
        logger.warning("ToT improvement generation failed: %s — falling back to standard", exc)
        return None


async def _generate_rewrite_plain_text(
    llm: object,
    input_text: str,
    improvements: list[Improvement],
    analysis_summary: str,
) -> str | None:
    """Generate a rewritten prompt as plain text (no JSON wrapping).

    This avoids the JSON truncation problem for large prompts: even if the
    LLM output is partially truncated, the text is still usable because
    there is no JSON structure to break.

    Args:
        llm: The LangChain chat model instance.
        input_text: The original prompt text.
        improvements: The list of improvements to incorporate.
        analysis_summary: Formatted dimension scores summary.

    Returns:
        The rewritten prompt text, or None on failure.
    """
    improvements_text = "\n".join(
        f"- [{imp.priority.value}] {imp.title}: {imp.suggestion}"
        for imp in improvements
    )

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=(
            "You are an expert prompt engineer. Rewrite the user's prompt "
            "incorporating ALL the improvements listed below. Output ONLY the "
            "rewritten prompt — no explanations, no JSON, no markdown fences."
        )),
        ("human", (
            "Original prompt:\n{input_text}\n\n"
            "Analysis:\n{analysis_summary}\n\n"
            "Improvements to apply:\n{improvements_text}\n\n"
            "Write the complete improved prompt below:"
        )),
    ])

    return await invoke_plain_text(
        llm, prompt,
        {
            "input_text": input_text,
            "analysis_summary": analysis_summary,
            "improvements_text": improvements_text,
        },
    )


async def _generate_large_prompt_improvements(
    llm: object,
    input_text: str,
    analysis_summary: str,
    overall_score: int,
    grade: str,
    output_quality_section: str,
    rag_section: str,
    prompt_type_guidance: str,
) -> dict:
    """Two-phase improvement generation for large prompts.

    Phase 1: Get improvements only as JSON (small output, always fits).
    Phase 2: Generate the rewritten prompt as plain text (no JSON wrapper,
             so partial output is still usable).

    Args:
        llm: The LangChain chat model instance.
        input_text: The original prompt text.
        analysis_summary: Formatted dimension scores summary.
        overall_score: The overall evaluation score.
        grade: The evaluation grade string.
        output_quality_section: Formatted output quality summary.
        rag_section: RAG context section.
        prompt_type_guidance: Prompt-type specific guidance text.

    Returns:
        Dict with ``improvements`` and ``rewritten_prompt``.
    """
    # Phase 1: Get improvements only (instruct LLM to skip rewrite)
    logger.info(
        "Large prompt detected (%d chars) — using two-phase improvement strategy",
        len(input_text),
    )
    improvements_only_prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=(
            "You are an expert prompt engineer. Given a prompt and its "
            "T.C.R.E.I. analysis, generate ONLY improvement suggestions.\n\n"
            f"{rag_section}\n\n{prompt_type_guidance}\n\n"
            "Based on the analysis, generate prioritized improvements:\n"
            "- CRITICAL: Missing core components\n"
            "- HIGH: Important missing elements\n"
            "- MEDIUM: Enhancements that improve quality\n"
            "- LOW: Polish and optimization\n\n"
            "If Output Quality Analysis data is provided, incorporate those "
            "findings into your improvements.\n\n"
            "Respond with ONLY valid JSON (no markdown):\n"
            '{{\n    "improvements": [\n'
            '        {{"priority": "CRITICAL|HIGH|MEDIUM|LOW", '
            '"title": "<short title>", '
            '"suggestion": "<specific actionable suggestion>"}}\n'
            "    ],\n"
            '    "rewritten_prompt": null\n'
            "}}"
        )),
        ("human", (
            "Original prompt:\n```\n{input_text}\n```\n\n"
            "Analysis results:\n{analysis_summary}\n\n"
            "Overall score: {overall_score}/100 ({grade})\n\n"
            "Output Quality Analysis:\n{output_quality_section}\n\n"
            "Generate improvement suggestions only (no rewritten prompt)."
        )),
    ])

    llm_result = await invoke_structured(
        llm, improvements_only_prompt,
        {
            "input_text": input_text,
            "analysis_summary": analysis_summary,
            "overall_score": overall_score,
            "grade": grade,
            "output_quality_section": output_quality_section,
        },
        ImprovementsLLMResponse,
    )

    if llm_result is not None and llm_result.improvements:
        improvements = [
            Improvement(
                priority=Priority(imp.priority),
                title=imp.title,
                suggestion=imp.suggestion,
            )
            for imp in llm_result.improvements
        ]
        logger.info("Phase 1 complete: %d improvements generated", len(improvements))
    else:
        logger.warning("Phase 1 failed — no improvements generated for large prompt")
        return {"improvements": [], "rewritten_prompt": None}

    # Phase 2: Generate rewrite as plain text (no JSON = no truncation breakage)
    rewritten = await _generate_rewrite_plain_text(
        llm, input_text, improvements, analysis_summary,
    )
    if rewritten:
        logger.info("Phase 2 complete: rewritten prompt generated (%d chars)", len(rewritten))
    else:
        logger.warning("Phase 2 failed — rewritten prompt could not be generated")

    return {
        "improvements": improvements,
        "rewritten_prompt": rewritten,
    }


async def generate_improvements(state: AgentState) -> dict:
    """Generate prioritized improvements and a rewritten prompt.

    Uses the analysis results to identify gaps and produce:
    1. A prioritized list of specific, actionable improvements
    2. A complete rewritten prompt incorporating all improvements

    For large prompts (>{_LARGE_PROMPT_THRESHOLD} chars), uses a two-phase
    strategy: improvements as JSON first, then rewrite as plain text.

    Args:
        state: Current agent state with dimension_scores, input_text, etc.

    Returns:
        State update dict with improvements, rewritten_prompt, and messages.
        On error, falls back to empty improvements.
    """
    try:
        llm = get_llm(state.get("llm_provider"))
        dimensions = state.get("dimension_scores", [])
        overall_score = state.get("overall_score", 0)
        grade = state.get("grade", "Weak")

        # Build analysis summary for the LLM
        analysis_summary = _build_analysis_summary(dimensions)

        # Build output quality summary if available
        output_eval: OutputEvaluationResult | None = state.get("output_evaluation")
        output_quality_section = _build_output_quality_summary(output_eval) if output_eval else "No output quality data available."

        # Retrieve relevant knowledge context via RAG
        rag_query = f"{state['input_text']}\n{analysis_summary}"
        rag_context = await retrieve_context(rag_query)
        rag_section = f"Relevant reference material:\n{rag_context}" if rag_context else ""

        # Inject document context if available (from uploaded documents)
        doc_context = state.get("document_context")
        if doc_context:
            doc_section = f"## Uploaded Document Context\n{doc_context}"
            rag_section = f"{rag_section}\n\n{doc_section}" if rag_section else doc_section

        # Inject historical improvements from similar evaluations
        similar_evals = state.get("similar_evaluations") or []
        if similar_evals:
            historical_section = _format_historical_improvements(similar_evals)
            if historical_section:
                rag_section = f"{rag_section}\n\n{historical_section}" if rag_section else historical_section

        # Select prompt type guidance based on router detection
        prompt_type = state.get("prompt_type", "initial")
        prompt_type_guidance = PROMPT_TYPE_CONTINUATION if prompt_type == "continuation" else PROMPT_TYPE_INITIAL

        # Append task-specific improvement guidance
        task_type = getattr(state.get("task_type"), "value", "general")
        task_prompts = get_prompts_for_task_type(task_type)
        if task_prompts.improvement_guidance:
            prompt_type_guidance = f"{prompt_type_guidance}\n\n{task_prompts.improvement_guidance}"

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=IMPROVEMENT_SYSTEM_PROMPT.format(
                rag_context=rag_section,
                prompt_type_guidance=prompt_type_guidance,
            )),
            ("human", (
                "Original prompt:\n```\n{input_text}\n```\n\n"
                "Analysis results:\n{analysis_summary}\n\n"
                "Overall score: {overall_score}/100 ({grade})\n\n"
                "Output Quality Analysis:\n{output_quality_section}\n\n"
                "Generate improvements and a rewritten version."
            )),
        ])

        input_text = state["input_text"]
        tot_branches_data = None

        if len(input_text) > _LARGE_PROMPT_THRESHOLD:
            # Large prompt: two-phase approach (improvements JSON + rewrite
            # as plain text) to avoid output truncation breaking JSON.
            result = await _generate_large_prompt_improvements(
                llm,
                input_text=input_text,
                analysis_summary=analysis_summary,
                overall_score=overall_score,
                grade=grade,
                output_quality_section=output_quality_section,
                rag_section=rag_section,
                prompt_type_guidance=prompt_type_guidance,
            )
        else:
            # Normal prompt: use Tree-of-Thought
            strategy = state.get("strategy")
            tot_num_branches = strategy.tot_num_branches if strategy else 3
            tot_result = await _generate_tot_improvements(
                llm,
                input_text=input_text,
                analysis_summary=analysis_summary,
                overall_score=overall_score,
                grade=grade,
                output_quality_section=output_quality_section,
                num_branches=tot_num_branches,
            )

            if tot_result is not None:
                result = tot_result
                tot_branches_data = tot_result.get("tot_branches_data")
            else:
                # Standard single-shot improvement path
                llm_result = await invoke_structured(
                    llm,
                    prompt,
                    {
                        "input_text": input_text,
                        "analysis_summary": analysis_summary,
                        "overall_score": overall_score,
                        "grade": grade,
                        "output_quality_section": output_quality_section,
                    },
                    ImprovementsLLMResponse,
                )

                if llm_result is not None:
                    result = _map_improvements_response(llm_result)
                else:
                    logger.warning("All parsing attempts failed for improvements — using empty fallback")
                    result = {"improvements": [], "rewritten_prompt": None}

        # Detect when optimization completely failed
        has_improvements = bool(result.get("improvements"))
        has_rewrite = bool(result.get("rewritten_prompt"))
        if has_improvements or has_rewrite:
            strategy_label = "two-phase" if len(input_text) > _LARGE_PROMPT_THRESHOLD else "ToT"
            step_message = f"Improvements generated ({strategy_label}) — here are your results."
        else:
            input_len = len(state.get("input_text", ""))
            logger.warning(
                "No improvements or rewritten prompt produced (input_length=%d). "
                "Likely caused by LLM output truncation on a very large prompt.",
                input_len,
            )
            step_message = (
                "Optimization was not possible for this prompt. "
                "The prompt is too long for the LLM to generate a complete "
                "rewritten version within its output limits. "
                "The analysis and scoring above are still valid. "
                "Try shortening your prompt or splitting it into smaller sections."
            )

        return {
            "improvements": result["improvements"],
            "rewritten_prompt": result["rewritten_prompt"],
            "evaluation_result": _build_evaluation_result(state, result),
            "tot_branches_data": tot_branches_data,
            "current_step": "improvements_complete",
            "should_continue": False,
            "messages": [AIMessage(content=step_message)],
        }

    except Exception as exc:
        logger.exception("generate_improvements failed: %s", exc)
        if is_fatal_llm_error(exc):
            return {
                "error_message": format_fatal_error(exc),
                "current_step": "error",
                "should_continue": False,
                "messages": [AIMessage(content=format_fatal_error(exc))],
            }
        domain_err = ImprovementError(
            f"Improvement generation failed: {exc}",
            context={"input_length": len(state.get("input_text", "")), "original_error": str(exc)},
        )
        logger.error("Domain error: %s context=%s", domain_err, domain_err.context)
        fallback = {"improvements": [], "rewritten_prompt": None}
        return {
            "improvements": [],
            "rewritten_prompt": None,
            "evaluation_result": _build_evaluation_result(state, fallback),
            "current_step": "improvements_complete",
            "should_continue": False,
            "messages": [
                AIMessage(content=f"Improvement generation failed: {type(exc).__name__}: {exc}. No suggestions available.")
            ],
        }


def _map_improvements_response(response: ImprovementsLLMResponse) -> dict:
    """Map an ImprovementsLLMResponse to domain models.

    Args:
        response: Parsed LLM response with improvement items and rewritten prompt.

    Returns:
        Dict with ``improvements`` (list of Improvement) and ``rewritten_prompt``.
    """
    improvements = [
        Improvement(
            priority=Priority(imp.priority),
            title=imp.title,
            suggestion=imp.suggestion,
        )
        for imp in response.improvements
    ]

    rewritten = response.rewritten_prompt

    if rewritten is None and improvements:
        logger.warning("LLM returned improvements but no rewritten_prompt")

    return {
        "improvements": improvements,
        "rewritten_prompt": rewritten,
    }


def _build_analysis_summary(dimensions: list) -> str:
    """Format dimension scores and findings for the LLM.

    Args:
        dimensions: List of DimensionScore objects from the analysis step.

    Returns:
        Human-readable markdown summary of found/missing sub-criteria.
    """
    parts = []
    for dim in dimensions:
        found = [sc for sc in dim.sub_criteria if sc.found]
        missing = [sc for sc in dim.sub_criteria if not sc.found]
        parts.append(
            f"**{dim.name.title()}** ({dim.score}/100):\n"
            f"  Found: {', '.join(sc.detail for sc in found) or 'Nothing detected'}\n"
            f"  Missing: {', '.join(sc.detail for sc in missing) or 'All criteria met'}"
        )
    return "\n\n".join(parts)


def _build_output_quality_summary(output_eval: OutputEvaluationResult) -> str:
    """Format output evaluation dimensions into text for the improver LLM.

    Args:
        output_eval: The output evaluation result with dimension scores.

    Returns:
        Human-readable summary of output quality dimensions and recommendations.
    """
    parts = [f"Overall output quality: {int(output_eval.overall_score * 100)}% ({output_eval.grade.value})"]
    for dim in output_eval.dimensions:
        pct = int(dim.score * 100)
        line = f"- **{dim.name.replace('_', ' ').title()}** ({pct}%): {dim.comment}"
        if dim.recommendation and dim.recommendation != "No change needed.":
            line += f"\n  Recommended fix: {dim.recommendation}"
        parts.append(line)
    return "\n".join(parts)


def _build_evaluation_result(state: AgentState, result: dict) -> EvaluationResult:
    """Assemble the final EvaluationResult from all state.

    Args:
        state: Current agent state with scores, dimensions, and flags.
        result: Dict with ``improvements`` and ``rewritten_prompt``.

    Returns:
        A fully populated EvaluationResult model.
    """
    return EvaluationResult(
        mode=state["mode"],
        input_text=state["input_text"],
        expected_outcome=state.get("expected_outcome"),
        overall_score=state.get("overall_score", 0),
        grade=Grade(state.get("grade", "Weak")),
        dimensions=state.get("dimension_scores", []),
        tcrei_flags=state.get("tcrei_flags"),
        improvements=result["improvements"],
        rewritten_prompt=result["rewritten_prompt"],
    )
