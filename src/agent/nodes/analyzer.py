"""Analyzer nodes — evaluate prompts against T.C.R.E.I. dimensions using an LLM."""

from __future__ import annotations

import asyncio
import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.agent.state import AgentState
from src.db import get_session_factory
from src.embeddings.service import find_similar_evaluations
from src.evaluator import DimensionScore, SubCriterionResult, TCREIFlags
from src.evaluator.criteria import get_criteria_for_task_type
from src.evaluator.exceptions import AnalysisError, format_fatal_error, is_fatal_llm_error
from src.evaluator.llm_schemas import AnalysisLLMResponse
from src.prompts import SYSTEM_PROMPT_ANALYSIS_TEMPLATE
from src.prompts.registry import get_prompts_for_task_type
from src.rag.knowledge_store import retrieve_context
from src.utils.chunking import aggregate_dimension_scores, chunk_prompt, should_chunk
from src.utils.llm_factory import get_llm
from src.utils.structured_output import invoke_structured

# Max concurrent chunk analysis calls to avoid rate-limiting
_CHUNK_CONCURRENCY = 5

logger = logging.getLogger(__name__)


def _build_criteria_description(task_type: str = "general") -> str:
    """Build a structured description of all criteria for the LLM.

    Args:
        task_type: The task type string ("general", "email_writing", or "summarization").

    Returns:
        Markdown-formatted criteria grouped by dimension.
    """
    criteria = get_criteria_for_task_type(task_type)
    sections = []
    for dimension_name, criteria_list in criteria.items():
        criteria_text = "\n".join(f"  - {c.name}: {c.description} (hint: {c.detection_hint})" for c in criteria_list)
        sections.append(f"### {dimension_name.upper()}\n{criteria_text}")
    return "\n\n".join(sections)


def _map_analysis_response(response: AnalysisLLMResponse) -> dict:
    """Map an AnalysisLLMResponse to domain models.

    Args:
        response: Parsed LLM response with dimension data and TCREI flags.

    Returns:
        Dict with ``dimensions`` (list of DimensionScore) and ``tcrei_flags``.
    """
    dimensions = []
    for dim_name in ["task", "context", "references", "constraints"]:
        dim_data = response.dimensions.get(dim_name)
        if dim_data is None:
            dimensions.append(DimensionScore(name=dim_name, score=0, sub_criteria=[]))
            continue

        sub_criteria = [
            SubCriterionResult(
                name=sc.name,
                found=sc.found,
                detail=sc.detail,
            )
            for sc in dim_data.sub_criteria
        ]
        dimensions.append(DimensionScore(
            name=dim_name,
            score=dim_data.score,
            sub_criteria=sub_criteria,
        ))

    tcrei_flags = TCREIFlags(
        task=response.tcrei_flags.task,
        context=response.tcrei_flags.context,
        references=response.tcrei_flags.references,
        evaluate=response.tcrei_flags.evaluate,
        iterate=response.tcrei_flags.iterate,
    )

    return {"dimensions": dimensions, "tcrei_flags": tcrei_flags}


async def _analyze_single(
    input_text: str,
    criteria_desc: str,
    rag_section: str,
    analysis_prompt: str = "",
    llm_provider: str | None = None,
    llm: BaseChatModel | None = None,
) -> dict:
    """Analyze a single (short) prompt via the LLM.

    Always applies Chain-of-Thought reasoning preamble.

    Args:
        input_text: The raw user prompt to evaluate.
        criteria_desc: Formatted criteria text for the system prompt.
        rag_section: RAG knowledge context to inject (may be empty).
        analysis_prompt: Override system prompt template (uses default if empty).
        llm_provider: Explicit LLM provider key (``"google"`` or ``"anthropic"``).
        llm: Pre-created LLM instance to reuse (avoids re-creation per chunk).

    Returns:
        Dict with ``dimensions`` and ``tcrei_flags``.
    """
    from src.prompts.strategies.cot import COT_ANALYSIS_PREAMBLE

    if llm is None:
        llm = get_llm(llm_provider)
    system_prompt = COT_ANALYSIS_PREAMBLE + analysis_prompt

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt.format(criteria=criteria_desc, rag_context=rag_section)),
        ("human", "Evaluate this prompt:\n\n```\n{input_text}\n```"),
    ])

    result = await invoke_structured(
        llm, prompt, {"input_text": input_text}, AnalysisLLMResponse,
    )

    if result is not None:
        return _map_analysis_response(result)

    logger.warning("All parsing attempts failed for analysis — using empty fallback")
    return _empty_analysis()


async def _analyze_chunked(
    input_text: str,
    criteria_desc: str,
    rag_section: str,
    analysis_prompt: str = "",
    llm_provider: str | None = None,
) -> tuple[dict, int]:
    """Analyze a long prompt by chunking it and aggregating results.

    Processes chunks concurrently (up to ``_CHUNK_CONCURRENCY`` at a time)
    and reuses a single LLM instance across all chunks.

    Args:
        input_text: The raw user prompt to evaluate.
        criteria_desc: Formatted criteria text for the system prompt.
        rag_section: RAG knowledge context to inject (may be empty).
        analysis_prompt: Override system prompt template (uses default if empty).
        llm_provider: Explicit LLM provider key.

    Returns:
        Tuple of (aggregated analysis dict, number of chunks).
    """
    chunks = chunk_prompt(input_text)
    logger.info("Chunking prompt into %d chunks for analysis", len(chunks))

    # Create LLM once and reuse for all chunks
    llm = get_llm(llm_provider)
    semaphore = asyncio.Semaphore(_CHUNK_CONCURRENCY)

    async def _process_chunk(idx: int, chunk_content: str) -> dict:
        async with semaphore:
            logger.info("Analyzing chunk %d/%d", idx + 1, len(chunks))
            return await _analyze_single(
                chunk_content, criteria_desc, rag_section, analysis_prompt,
                llm=llm,
            )

    tasks = [
        _process_chunk(i, chunk.content)
        for i, chunk in enumerate(chunks)
    ]
    chunk_scores = await asyncio.gather(*tasks)
    chunk_tokens = [chunk.token_estimate for chunk in chunks]

    aggregated = aggregate_dimension_scores(list(chunk_scores), chunk_tokens)
    return aggregated, len(chunks)


def _format_historical_context(similar_evals: list[dict]) -> str:
    """Format past evaluations into context for the LLM.

    Args:
        similar_evals: List of similar evaluation dicts from embedding search.

    Returns:
        Markdown-formatted string describing past evaluations.
    """
    lines = ["## Lessons from Previous Evaluations"]
    for i, ev in enumerate(similar_evals[:3], 1):
        score = ev["overall_score"]
        grade = ev["grade"]
        preview = ev["input_text"][:120]
        lines.append(f"{i}. Similar prompt (score: {score}/100 - {grade}): \"{preview}...\"")
        if ev.get("improvements_summary"):
            lines.append(f"   Key improvements applied: {ev['improvements_summary'][:200]}")
        if ev.get("rewritten_prompt"):
            lines.append("   Rewritten version available (scored higher)")
    return "\n".join(lines)


async def _retrieve_similar_evaluations(input_text: str, user_id: str | None) -> list[dict]:
    """Retrieve similar past evaluations from the embedding store.

    Args:
        input_text: The prompt text to find similar evaluations for.
        user_id: Optional user ID to scope the search.

    Returns:
        List of similar evaluation dicts, or empty list on failure.
    """
    try:
        factory = get_session_factory()
        async with factory() as session:
            return await find_similar_evaluations(
                session, query_text=input_text, user_id=user_id,
            )
    except Exception as exc:
        logger.warning("Failed to retrieve similar evaluations: %s", exc)
    return []


async def analyze_prompt(state: AgentState) -> dict:
    """Analyze a user prompt against T.C.R.E.I. dimensions.

    Uses the LLM to evaluate each criterion, returning structured scores
    and detailed findings. For long prompts (2000+ estimated tokens),
    splits into chunks and aggregates per-chunk scores.

    Returns:
        State update dict with dimension_scores, tcrei_flags, and messages.
        On error, returns empty analysis fallback.
    """
    try:
        # Select criteria and analysis prompt based on task type
        task_type = getattr(state.get("task_type"), "value", "general")
        criteria_desc = _build_criteria_description(task_type)
        task_prompts = get_prompts_for_task_type(task_type)
        analysis_prompt = task_prompts.analysis

        input_text = state["input_text"]

        # Retrieve relevant knowledge context via RAG
        rag_context = await retrieve_context(input_text)
        rag_section = f"Relevant reference material:\n{rag_context}" if rag_context else ""

        # Inject document context if available (from uploaded documents)
        doc_context = state.get("document_context")
        if doc_context:
            doc_section = f"## Uploaded Document Context\n{doc_context}"
            rag_section = f"{rag_section}\n\n{doc_section}" if rag_section else doc_section

        # Retrieve similar past evaluations for self-learning
        similar_evals = await _retrieve_similar_evaluations(
            input_text, state.get("user_id"),
        )
        if similar_evals:
            historical_section = _format_historical_context(similar_evals)
            rag_section = f"{rag_section}\n\n{historical_section}" if rag_section else historical_section

        chunk_count = None
        llm_provider = state.get("llm_provider")
        # CoT is always applied (preamble prepended inside _analyze_single)
        if should_chunk(input_text):
            analysis, chunk_count = await _analyze_chunked(
                input_text, criteria_desc, rag_section, analysis_prompt,
                llm_provider=llm_provider,
            )
        else:
            analysis = await _analyze_single(
                input_text, criteria_desc, rag_section, analysis_prompt,
                llm_provider=llm_provider,
            )

        # Build CoT reasoning trace from dimension findings
        cot_trace_parts = []
        for dim in analysis["dimensions"]:
            found = [sc.detail for sc in dim.sub_criteria if sc.found]
            missing = [sc.detail for sc in dim.sub_criteria if not sc.found]
            cot_trace_parts.append(
                f"STEP — {dim.name.upper()} ({dim.score}/100):\n"
                f"  Found: {', '.join(found) or 'Nothing detected'}\n"
                f"  Missing: {', '.join(missing) or 'All criteria met'}"
            )
        cot_reasoning_trace = "\n\n".join(cot_trace_parts) if cot_trace_parts else None

        result: dict = {
            "dimension_scores": analysis["dimensions"],
            "tcrei_flags": analysis["tcrei_flags"],
            "similar_evaluations": similar_evals or None,
            "cot_reasoning_trace": cot_reasoning_trace,
            "current_step": "analysis_complete",
            "messages": [
                AIMessage(content="📊 Analysis complete (CoT) — scoring each dimension...")
            ],
        }

        if chunk_count is not None:
            result["chunk_count"] = chunk_count

        return result

    except Exception as exc:
        logger.exception("analyze_prompt failed: %s", exc)
        if is_fatal_llm_error(exc):
            return {
                "error_message": format_fatal_error(exc),
                "current_step": "error",
                "should_continue": False,
                "messages": [AIMessage(content=format_fatal_error(exc))],
            }
        domain_err = AnalysisError(
            f"Prompt analysis failed: {exc}",
            context={"input_length": len(state.get("input_text", "")), "original_error": str(exc)},
        )
        logger.error("Domain error: %s context=%s", domain_err, domain_err.context)
        analysis = _empty_analysis()
        return {
            "dimension_scores": analysis["dimensions"],
            "tcrei_flags": analysis["tcrei_flags"],
            "current_step": "analysis_complete",
            "messages": [
                AIMessage(content=f"Analysis failed: {type(exc).__name__}: {exc}. Using fallback zero scores.")
            ],
        }


async def analyze_system_prompt(state: AgentState) -> dict:
    """Analyze a system prompt against T.C.R.E.I. dimensions.

    Evaluates whether the system prompt will reliably produce
    the expected outcome.

    Returns:
        State update dict with dimension_scores, tcrei_flags, and messages.
        On error, returns empty analysis fallback.
    """
    try:
        llm = get_llm(state.get("llm_provider"))
        task_type = getattr(state.get("task_type"), "value", "general")
        criteria_desc = _build_criteria_description(task_type)
        input_text = state["input_text"]

        # Retrieve relevant knowledge context via RAG
        rag_context = await retrieve_context(input_text)
        rag_section = f"Relevant reference material:\n{rag_context}" if rag_context else ""

        # Inject document context if available (from uploaded documents)
        doc_context = state.get("document_context")
        if doc_context:
            doc_section = f"## Uploaded Document Context\n{doc_context}"
            rag_section = f"{rag_section}\n\n{doc_section}" if rag_section else doc_section

        # CoT preamble always applied for system prompt analysis
        from src.prompts.strategies.cot import COT_ANALYSIS_PREAMBLE
        system_prompt_text = COT_ANALYSIS_PREAMBLE + SYSTEM_PROMPT_ANALYSIS_TEMPLATE.format(criteria=criteria_desc, rag_context=rag_section)

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_text),
            ("human", "Evaluate this system prompt:\n\n```\n{input_text}\n```\n\nExpected outcome:\n{expected_outcome}"),
        ])

        result = await invoke_structured(
            llm,
            prompt,
            {
                "input_text": state["input_text"],
                "expected_outcome": state.get("expected_outcome", "Not specified"),
            },
            AnalysisLLMResponse,
        )

        if result is not None:
            analysis = _map_analysis_response(result)
        else:
            logger.warning("All parsing attempts failed for system prompt analysis — using empty fallback")
            analysis = _empty_analysis()

        return {
            "dimension_scores": analysis["dimensions"],
            "tcrei_flags": analysis["tcrei_flags"],
            "current_step": "analysis_complete",
            "messages": [
                AIMessage(content="📊 System prompt analysis complete — scoring dimensions...")
            ],
        }

    except Exception as exc:
        logger.exception("analyze_system_prompt failed: %s", exc)
        if is_fatal_llm_error(exc):
            return {
                "error_message": format_fatal_error(exc),
                "current_step": "error",
                "should_continue": False,
                "messages": [AIMessage(content=format_fatal_error(exc))],
            }
        domain_err = AnalysisError(
            f"System prompt analysis failed: {exc}",
            context={"input_length": len(state.get("input_text", "")), "original_error": str(exc)},
        )
        logger.error("Domain error: %s context=%s", domain_err, domain_err.context)
        analysis = _empty_analysis()
        return {
            "dimension_scores": analysis["dimensions"],
            "tcrei_flags": analysis["tcrei_flags"],
            "current_step": "analysis_complete",
            "messages": [
                AIMessage(content=f"System prompt analysis failed: {type(exc).__name__}: {exc}. Using fallback zero scores.")
            ],
        }


def _empty_analysis() -> dict:
    """Return an empty analysis structure as fallback.

    Returns:
        Dict with zero-scored dimensions and default TCREIFlags.
    """
    dimensions = [
        DimensionScore(name=name, score=0, sub_criteria=[])
        for name in ["task", "context", "references", "constraints"]
    ]
    return {
        "dimensions": dimensions,
        "tcrei_flags": TCREIFlags(),
    }
