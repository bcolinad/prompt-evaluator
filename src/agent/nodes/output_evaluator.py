"""Output evaluator node — LLM-as-Judge scoring of generated output."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tracers.context import collect_runs

from src.agent.state import AgentState
from src.config import get_settings
from src.evaluator import Grade, OutputDimensionScore, OutputEvaluationResult
from src.evaluator.exceptions import OutputEvaluationError, format_fatal_error, is_fatal_llm_error
from src.evaluator.llm_schemas import OutputEvaluationLLMResponse
from src.prompts.registry import get_prompts_for_task_type
from src.utils.langsmith_utils import score_run
from src.utils.llm_factory import get_llm
from src.utils.structured_output import invoke_structured

logger = logging.getLogger(__name__)



async def evaluate_output(state: AgentState) -> dict:
    """Evaluate LLM output quality using LLM-as-Judge.

    Scores the output on 5 dimensions, attaches scores to LangSmith
    run as feedback, and returns an OutputEvaluationResult.
    For email_writing task type, uses email-specific dimensions.

    Args:
        state: Current agent state with input_text and llm_output.

    Returns:
        State update dict with output_evaluation and messages.
        On error, returns empty output evaluation fallback.
    """
    try:

        llm = get_llm(state.get("llm_provider"))
        llm_output = state.get("llm_output", "")
        input_text = state["input_text"]

        # Select output evaluation prompt based on task type
        task_type = getattr(state.get("task_type"), "value", "general")
        task_prompts = get_prompts_for_task_type(task_type)
        eval_system_prompt = task_prompts.output_evaluation

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=eval_system_prompt),
            ("human", "Original prompt:\n```\n{input_text}\n```\n\nLLM Output:\n```\n{llm_output}\n```"),
        ])

        variables = {"input_text": input_text, "llm_output": llm_output}

        # Use collect_runs to capture the LangSmith run ID
        run_id = None
        parsed: OutputEvaluationLLMResponse | None = None

        with collect_runs() as cb:
            parsed = await invoke_structured(llm, prompt, variables, OutputEvaluationLLMResponse)
            if cb.traced_runs:
                run_id = str(cb.traced_runs[0].id)
            else:
                logger.debug("No run_id captured from collect_runs — LangSmith tracing may be disabled")

        if parsed is not None:
            result = _map_output_evaluation(parsed, state, run_id)
        else:
            result = _empty_output_evaluation(state, run_id, task_type)

        # Score each dimension in LangSmith
        if run_id:
            for dim in result.dimensions:
                score_run(run_id, dim.name, dim.score, dim.comment)

        return {
            "output_evaluation": result,
            "current_step": "output_evaluated",
            "messages": [
                AIMessage(content="📊 Output evaluation complete — building report...")
            ],
        }

    except Exception as exc:
        logger.exception("evaluate_output failed: %s", exc)
        if is_fatal_llm_error(exc):
            return {
                "error_message": format_fatal_error(exc),
                "current_step": "error",
                "should_continue": False,
                "messages": [AIMessage(content=format_fatal_error(exc))],
            }
        domain_err = OutputEvaluationError(
            f"Output evaluation failed: {exc}",
            context={"input_length": len(state.get("input_text", "")), "original_error": str(exc)},
        )
        logger.error("Domain error: %s context=%s", domain_err, domain_err.context)
        task_type = getattr(state.get("task_type"), "value", "general")
        result = _empty_output_evaluation(state, None, task_type)
        return {
            "output_evaluation": result,
            "current_step": "output_evaluated",
            "messages": [
                AIMessage(content=f"Output evaluation failed: {type(exc).__name__}: {exc}. Using fallback scores.")
            ],
        }


def _map_output_evaluation(
    parsed: OutputEvaluationLLMResponse,
    state: AgentState,
    run_id: str | None,
) -> OutputEvaluationResult:
    """Map a parsed LLM response to an OutputEvaluationResult.

    Args:
        parsed: Structured LLM response with dimension scores.
        state: Current agent state with input_text and llm_output.
        run_id: LangSmith run ID for feedback attachment (may be None).

    Returns:
        A fully populated OutputEvaluationResult.
    """
    settings = get_settings()
    llm_provider = state.get("llm_provider", settings.llm_provider.value)
    dimensions = [
        OutputDimensionScore(
            name=dim.name,
            score=dim.score,
            comment=dim.comment,
            recommendation=dim.recommendation,
        )
        for dim in parsed.dimensions
    ]

    grade = _score_to_grade(parsed.overall_score)

    return OutputEvaluationResult(
        prompt_used=state["input_text"],
        llm_output=state.get("llm_output", ""),
        provider=llm_provider,
        model=_get_model_name(settings),
        dimensions=dimensions,
        overall_score=parsed.overall_score,
        grade=grade,
        langsmith_run_id=run_id,
        findings=parsed.findings,
    )


def _score_to_grade(score: float) -> Grade:
    """Convert a 0-1 score to a Grade enum.

    Args:
        score: Float between 0.0 and 1.0.

    Returns:
        Corresponding Grade (Excellent, Good, Needs Work, or Weak).
    """
    pct = score * 100
    if pct >= 85:
        return Grade.EXCELLENT
    elif pct >= 65:
        return Grade.GOOD
    elif pct >= 40:
        return Grade.NEEDS_WORK
    return Grade.WEAK


def _get_model_name(settings: object) -> str:
    """Get the current model name from settings based on the active provider.

    Args:
        settings: Settings object with llm_provider, google_model, and anthropic_model.

    Returns:
        Model name string, or "unknown" if not determinable.
    """
    provider = getattr(settings, "llm_provider", None)
    provider_value = getattr(provider, "value", str(provider)) if provider else ""
    if provider_value == "google":
        return getattr(settings, "google_model", "unknown")
    return getattr(settings, "anthropic_model", "unknown")


async def _evaluate_output_common(
    llm: object,
    prompt_text: str,
    output_text: str,
    task_type: str = "general",
) -> OutputEvaluationResult:
    """Shared helper to evaluate any prompt+output pair via LLM-as-Judge.

    Args:
        llm: The LangChain chat model instance.
        prompt_text: The prompt that produced the output.
        output_text: The generated output to evaluate.
        task_type: Task type for selecting evaluation criteria.

    Returns:
        An OutputEvaluationResult with dimension scores.
    """
    task_prompts = get_prompts_for_task_type(task_type)
    eval_system_prompt = task_prompts.output_evaluation

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=eval_system_prompt),
        ("human", "Original prompt:\n```\n{input_text}\n```\n\nLLM Output:\n```\n{llm_output}\n```"),
    ])

    variables = {"input_text": prompt_text, "llm_output": output_text}

    run_id = None
    parsed: OutputEvaluationLLMResponse | None = None

    with collect_runs() as cb:
        parsed = await invoke_structured(llm, prompt, variables, OutputEvaluationLLMResponse)
        if cb.traced_runs:
            run_id = str(cb.traced_runs[0].id)

    if parsed is not None:
        settings = get_settings()
        llm_provider = settings.llm_provider.value
        dimensions = [
            OutputDimensionScore(
                name=dim.name,
                score=dim.score,
                comment=dim.comment,
                recommendation=dim.recommendation,
            )
            for dim in parsed.dimensions
        ]
        grade = _score_to_grade(parsed.overall_score)

        result = OutputEvaluationResult(
            prompt_used=prompt_text,
            llm_output=output_text,
            provider=llm_provider,
            model=_get_model_name(settings),
            dimensions=dimensions,
            overall_score=parsed.overall_score,
            grade=grade,
            langsmith_run_id=run_id,
            findings=parsed.findings,
        )

        # Score each dimension in LangSmith
        if run_id:
            for dim in result.dimensions:
                score_run(run_id, dim.name, dim.score, dim.comment)

        return result

    # Fallback
    settings = get_settings()
    task_prompts_fb = get_prompts_for_task_type(task_type)
    fallback = task_prompts_fb.fallback_dimensions
    dimensions = [
        OutputDimensionScore(
            name=name,
            score=0.0,
            comment=comment,
            recommendation="Evaluation failed — retry to get actionable recommendations.",
        )
        for name, comment in fallback
    ]
    return OutputEvaluationResult(
        prompt_used=prompt_text,
        llm_output=output_text,
        provider=settings.llm_provider.value,
        model=_get_model_name(settings),
        dimensions=dimensions,
        overall_score=0.0,
        grade=Grade.WEAK,
        langsmith_run_id=run_id,
        findings=["Evaluation failed — could not parse LLM judge response."],
    )


async def evaluate_optimized_output(state: AgentState) -> dict:
    """Evaluate the optimized prompt's output quality using LLM-as-Judge.

    If no optimized output is available, skips gracefully.

    Args:
        state: Current agent state with optimized_output_summary and rewritten_prompt.

    Returns:
        State update dict with optimized_output_evaluation and messages.
    """
    optimized_summary = state.get("optimized_output_summary")
    rewritten_prompt = state.get("rewritten_prompt")

    if not optimized_summary or not rewritten_prompt:
        logger.info("No optimized output available — skipping optimized evaluation")
        return {
            "optimized_output_evaluation": None,
            "current_step": "optimized_output_evaluated",
            "messages": [
                AIMessage(content="No optimized output to evaluate — skipping.")
            ],
        }

    try:
        llm = get_llm(state.get("llm_provider"))
        task_type = getattr(state.get("task_type"), "value", "general")

        result = await _evaluate_output_common(
            llm, rewritten_prompt, optimized_summary, task_type,
        )

        return {
            "optimized_output_evaluation": result,
            "current_step": "optimized_output_evaluated",
            "messages": [
                AIMessage(content="Optimized output evaluation complete — running meta-evaluation...")
            ],
        }

    except Exception as exc:
        logger.exception("evaluate_optimized_output failed: %s", exc)
        if is_fatal_llm_error(exc):
            return {
                "error_message": format_fatal_error(exc),
                "current_step": "error",
                "should_continue": False,
                "messages": [AIMessage(content=format_fatal_error(exc))],
            }
        return {
            "optimized_output_evaluation": None,
            "current_step": "optimized_output_evaluated",
            "messages": [
                AIMessage(content=f"Optimized output evaluation failed: {type(exc).__name__}: {exc}. Skipping.")
            ],
        }


def _empty_output_evaluation(
    state: AgentState, run_id: str | None, task_type: str = "general",
) -> OutputEvaluationResult:
    """Return a fallback evaluation result with placeholder dimensions.

    Args:
        state: Current agent state with input_text and llm_output.
        run_id: LangSmith run ID (may be None).
        task_type: Task type for selecting appropriate fallback dimensions.

    Returns:
        An OutputEvaluationResult with zero scores and failure messages.
    """
    settings = get_settings()
    task_prompts = get_prompts_for_task_type(task_type)
    fallback = task_prompts.fallback_dimensions
    dimensions = [
        OutputDimensionScore(
            name=name,
            score=0.0,
            comment=comment,
            recommendation="Evaluation failed — retry to get actionable recommendations.",
        )
        for name, comment in fallback
    ]
    return OutputEvaluationResult(
        prompt_used=state["input_text"],
        llm_output=state.get("llm_output", ""),
        provider=settings.llm_provider.value,
        model=_get_model_name(settings),
        dimensions=dimensions,
        overall_score=0.0,
        grade=Grade.WEAK,
        langsmith_run_id=run_id,
        findings=["Evaluation failed — could not parse LLM judge response."],
    )
