"""LangGraph state schema for the prompt evaluator agent."""

from __future__ import annotations

from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.evaluator import (
    DimensionScore,
    EvalMode,
    EvalPhase,
    EvaluationResult,
    FullEvaluationReport,
    Improvement,
    MetaAssessment,
    OutputEvaluationResult,
    TaskType,
    TCREIFlags,
    ToTBranchesAuditData,
)
from src.evaluator.strategies import StrategyConfig


class AgentState(TypedDict):
    """State passed between LangGraph nodes.

    The `messages` field uses LangGraph's message reducer to
    automatically append new messages to the conversation history.
    """

    # Conversation history (auto-appended via reducer)
    messages: Annotated[list[BaseMessage], add_messages]

    # Input
    input_text: str
    mode: EvalMode
    eval_phase: EvalPhase | None
    expected_outcome: str | None
    session_id: str
    thread_id: str | None
    user_id: str | None
    task_type: TaskType | None
    prompt_type: str | None
    llm_provider: str | None

    # Analysis (populated by analyzer node)
    dimension_scores: list[DimensionScore] | None
    tcrei_flags: TCREIFlags | None

    # Scoring (populated by scorer node)
    overall_score: int | None
    grade: str | None

    # Improvements (populated by improver node)
    improvements: list[Improvement] | None
    rewritten_prompt: str | None

    # Final result (populated by improver node)
    evaluation_result: EvaluationResult | None

    # Output evaluation (populated by output nodes)
    llm_output: str | None
    output_evaluation: OutputEvaluationResult | None

    # Combined report (populated by report_builder node)
    full_report: FullEvaluationReport | None

    # Self-learning (populated by analyzer node from embedding search)
    similar_evaluations: list | None

    # Chunking metadata (populated by analyzer node for long prompts)
    chunk_count: int | None

    # Control flow
    current_step: str | None
    should_continue: bool
    followup_action: str | None

    # Strategy configuration (controls CoT, ToT, Meta enhancements)
    strategy: StrategyConfig | None

    # Multi-execution configuration
    execution_count: int | None  # Number of times to execute each prompt (default 2)
    original_outputs: list[str] | None  # N outputs from original prompt
    original_output_summary: str | None  # Formatted aggregate of N original outputs
    optimized_outputs: list[str] | None  # N outputs from optimized prompt
    optimized_output_summary: str | None  # Formatted aggregate of N optimized outputs
    optimized_output_evaluation: OutputEvaluationResult | None  # Quality eval for optimized prompt

    # CoT/ToT audit trail
    cot_reasoning_trace: str | None  # CoT reasoning captured during analysis
    tot_branches_data: ToTBranchesAuditData | None  # ToT exploration audit trail

    # Meta-evaluation (populated by meta_evaluator node)
    meta_assessment: MetaAssessment | None
    meta_findings: list[str] | None

    # Document context (populated by UI layer before graph invocation)
    document_context: str | None
    document_ids: list[str] | None
    document_summary: str | None

    # Fatal error — stops the pipeline and shows the error to the user
    error_message: str | None
