"""High-level evaluation service — orchestrates graph invocation and returns clean results.

Provides a ``PromptEvaluationService`` that always uses the enhanced strategy
(CoT+ToT+Meta), invokes the LangGraph pipeline, and returns an ``EvaluationReport``
dataclass with all relevant outputs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage

from src.agent.graph import get_graph
from src.evaluator import (
    EvalMode,
    EvalPhase,
    FullEvaluationReport,
    MetaAssessment,
    OutputEvaluationResult,
    TaskType,
)
from src.evaluator.exceptions import EvaluatorError
from src.evaluator.strategies import get_default_strategy

logger = logging.getLogger(__name__)


@dataclass
class EvaluationReport:
    """Clean result object returned by ``PromptEvaluationService.evaluate()``.

    Attributes:
        full_report: The assembled ``FullEvaluationReport`` from the pipeline.
        overall_score: Weighted structure score (0-100).
        grade: Letter grade (Excellent / Good / Needs Work / Weak).
        strategy_used: Human-readable label for the strategy that was applied.
        meta_assessment: Meta-evaluation self-assessment scores.
        optimized_output_evaluation: Quality evaluation for the optimized prompt output.
        error: Error message string when the evaluation failed.
    """

    full_report: FullEvaluationReport | None = None
    overall_score: int = 0
    grade: str = "Weak"
    strategy_used: str = "enhanced (CoT+ToT+Meta)"
    meta_assessment: MetaAssessment | None = None
    optimized_output_evaluation: OutputEvaluationResult | None = None
    error: str | None = None


class PromptEvaluationService:
    """Orchestrates prompt evaluation via the LangGraph pipeline.

    Always uses the enhanced strategy (CoT+ToT+Meta).

    Attributes:
        llm_provider: Default LLM provider key (``"google"``, ``"anthropic"``, ``"ollama"``).
    """

    def __init__(
        self,
        llm_provider: str = "google",
    ) -> None:
        self.llm_provider = llm_provider

    async def evaluate(
        self,
        prompt_text: str,
        *,
        execution_count: int = 2,
        task_type: TaskType = TaskType.GENERAL,
        eval_phase: EvalPhase = EvalPhase.FULL,
        mode: EvalMode = EvalMode.PROMPT,
        session_id: str = "default",
        user_id: str = "anonymous",
        thread_id: str | None = None,
        llm_provider: str | None = None,
    ) -> EvaluationReport:
        """Run a full evaluation and return a clean report.

        Always uses enhanced strategy (CoT+ToT+Meta).

        Args:
            prompt_text: The prompt to evaluate.
            execution_count: Number of times to execute each prompt (2-5).
            task_type: Task type for criteria selection.
            eval_phase: Evaluation phase (STRUCTURE, OUTPUT, FULL).
            mode: Evaluation mode (PROMPT or SYSTEM_PROMPT).
            session_id: Session identifier for grouping evaluations.
            user_id: User identifier for embedding ownership.
            thread_id: Chainlit thread ID for cleanup tracking.
            llm_provider: Override LLM provider for this evaluation.

        Returns:
            An ``EvaluationReport`` with evaluation results or an error message.
        """
        strategy_config = get_default_strategy()

        initial_state: dict[str, Any] = {
            "messages": [HumanMessage(content=prompt_text)],
            "input_text": prompt_text,
            "mode": mode,
            "eval_phase": eval_phase,
            "expected_outcome": None,
            "session_id": session_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "task_type": task_type,
            "llm_provider": llm_provider or self.llm_provider,
            "strategy": strategy_config,
            "execution_count": execution_count,
            "should_continue": False,
        }

        try:
            final_state: dict[str, Any] = {}
            async for event in get_graph().astream(  # type: ignore[attr-defined]
                initial_state, stream_mode="updates"
            ):
                for _node_name, state_update in event.items():
                    if isinstance(state_update, dict):
                        final_state.update(state_update)

            # Check for fatal error
            error_msg = final_state.get("error_message")
            if error_msg:
                return EvaluationReport(error=error_msg)

            report: FullEvaluationReport | None = final_state.get("full_report")
            if not report:
                return EvaluationReport(error="Evaluation produced no report.")

            return EvaluationReport(
                full_report=report,
                overall_score=final_state.get("overall_score", 0),
                grade=final_state.get("grade", "Weak"),
                strategy_used=report.strategy_used,
                meta_assessment=final_state.get("meta_assessment"),
                optimized_output_evaluation=final_state.get("optimized_output_evaluation"),
            )

        except EvaluatorError as exc:
            logger.exception("Evaluation failed with domain error: %s", exc)
            return EvaluationReport(error=str(exc))
        except Exception as exc:
            logger.exception("Unexpected evaluation error: %s", exc)
            return EvaluationReport(error=f"Unexpected error: {type(exc).__name__}: {exc}")
