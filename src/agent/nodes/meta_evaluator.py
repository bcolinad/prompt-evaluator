"""Meta-evaluator node — self-reflection pass that evaluates the evaluation itself."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.agent.state import AgentState
from src.evaluator import Improvement, MetaAssessment, Priority
from src.evaluator.exceptions import MetaEvaluationError, format_fatal_error, is_fatal_llm_error
from src.evaluator.llm_schemas import MetaEvaluationLLMResponse
from src.prompts.strategies.meta import META_EVALUATION_PROMPT
from src.utils.llm_factory import get_llm
from src.utils.structured_output import invoke_structured

logger = logging.getLogger(__name__)


def _build_dimension_summary(dimensions: list) -> str:
    """Format dimension scores for the meta-evaluation prompt.

    Args:
        dimensions: List of DimensionScore objects.

    Returns:
        Markdown-formatted dimension summary.
    """
    if not dimensions:
        return "No dimension scores available."
    parts = []
    for dim in dimensions:
        found = sum(1 for sc in dim.sub_criteria if sc.found)
        total = len(dim.sub_criteria)
        parts.append(f"- **{dim.name.title()}**: {dim.score}/100 ({found}/{total} sub-criteria met)")
    return "\n".join(parts)


def _build_improvements_text(improvements: list) -> str:
    """Format improvements for the meta-evaluation prompt.

    Args:
        improvements: List of Improvement objects.

    Returns:
        Markdown-formatted improvements list.
    """
    if not improvements:
        return "No improvements were suggested."
    parts = []
    for imp in improvements:
        priority = imp.priority.value if hasattr(imp.priority, "value") else str(imp.priority)
        parts.append(f"- [{priority}] **{imp.title}**: {imp.suggestion}")
    return "\n".join(parts)


async def meta_evaluate(state: AgentState) -> dict:
    """Evaluate the evaluation itself and refine results.

    Performs a self-reflection pass using the Meta Prompting strategy:
    - Assesses accuracy, completeness, actionability, and faithfulness
    - Identifies missed improvements
    - Optionally refines the rewritten prompt

    Args:
        state: Current agent state with evaluation results.

    Returns:
        State update dict with meta_assessment, meta_findings, and
        optionally updated rewritten_prompt and merged improvements.
    """
    try:
        llm = get_llm(state.get("llm_provider"))

        dimension_summary = _build_dimension_summary(state.get("dimension_scores", []))
        improvements_text = _build_improvements_text(state.get("improvements", []))
        rewritten_prompt = state.get("rewritten_prompt") or "No rewritten prompt was generated."

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=META_EVALUATION_PROMPT.format(
                input_text=state["input_text"],
                overall_score=state.get("overall_score", 0),
                grade=state.get("grade", "Weak"),
                dimension_summary=dimension_summary,
                improvements_text=improvements_text,
                rewritten_prompt=rewritten_prompt,
            )),
            ("human", "Evaluate the quality of this evaluation and suggest refinements."),
        ])

        result = await invoke_structured(
            llm, prompt, {}, MetaEvaluationLLMResponse,
        )

        if result is None:
            logger.warning("Meta-evaluation returned no result — skipping meta refinement")
            return {
                "meta_assessment": None,
                "meta_findings": ["Meta-evaluation could not produce results."],
                "current_step": "meta_evaluate_complete",
                "messages": [
                    AIMessage(content="Meta-evaluation skipped — could not parse self-assessment.")
                ],
            }

        # Map meta assessment
        meta_assessment = MetaAssessment(
            accuracy_score=result.meta_assessment.accuracy_score,
            completeness_score=result.meta_assessment.completeness_score,
            actionability_score=result.meta_assessment.actionability_score,
            faithfulness_score=result.meta_assessment.faithfulness_score,
            overall_confidence=result.meta_assessment.overall_confidence,
        )

        # Merge refined improvements with existing ones
        state_update: dict = {
            "meta_assessment": meta_assessment,
            "meta_findings": result.meta_findings or [],
            "current_step": "meta_evaluate_complete",
            "messages": [
                AIMessage(content="Meta-evaluation complete — self-assessment applied.")
            ],
        }

        # If meta-evaluation produced refined improvements, merge them
        if result.refined_improvements:
            existing = list(state.get("improvements") or [])
            for imp in result.refined_improvements:
                existing.append(Improvement(
                    priority=Priority(imp.priority),
                    title=f"[Meta] {imp.title}",
                    suggestion=imp.suggestion,
                ))
            state_update["improvements"] = existing

        # If meta-evaluation refined the rewritten prompt, use it
        if result.refined_rewritten_prompt:
            state_update["rewritten_prompt"] = result.refined_rewritten_prompt

        return state_update

    except Exception as exc:
        logger.exception("meta_evaluate failed: %s", exc)
        if is_fatal_llm_error(exc):
            return {
                "error_message": format_fatal_error(exc),
                "current_step": "error",
                "should_continue": False,
                "messages": [AIMessage(content=format_fatal_error(exc))],
            }
        domain_err = MetaEvaluationError(
            f"Meta-evaluation failed: {exc}",
            context={"original_error": str(exc)},
        )
        logger.error("Domain error: %s context=%s", domain_err, domain_err.context)
        return {
            "meta_assessment": None,
            "meta_findings": [f"Meta-evaluation failed: {exc}"],
            "current_step": "meta_evaluate_complete",
            "messages": [
                AIMessage(content=f"Meta-evaluation failed: {type(exc).__name__}: {exc}. Skipping self-assessment.")
            ],
        }
