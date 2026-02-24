"""LangGraph StateGraph definition for the prompt evaluator agent."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.agent.nodes.analyzer import analyze_prompt, analyze_system_prompt
from src.agent.nodes.conversational import handle_followup
from src.agent.nodes.improver import generate_improvements
from src.agent.nodes.meta_evaluator import meta_evaluate
from src.agent.nodes.optimized_runner import run_optimized_prompt
from src.agent.nodes.output_evaluator import evaluate_optimized_output, evaluate_output
from src.agent.nodes.output_runner import run_prompt_for_output
from src.agent.nodes.report_builder import build_report
from src.agent.nodes.router import route_input
from src.agent.nodes.scorer import score_prompt
from src.agent.state import AgentState
from src.evaluator import EvalMode, EvalPhase


def _has_fatal_error(state: AgentState) -> bool:
    """Check if a fatal error has been set, requiring pipeline abort."""
    return bool(state.get("error_message"))


def _route_by_phase(state: AgentState) -> str:
    """Route based on eval_phase: STRUCTURE/FULL -> analyzer, OUTPUT -> output runner."""
    phase = state.get("eval_phase") or EvalPhase.STRUCTURE
    if phase == EvalPhase.OUTPUT:
        return "run_prompt_for_output"
    # STRUCTURE or FULL -> go through structural analysis first
    if state["mode"] == EvalMode.SYSTEM_PROMPT:
        return "analyze_system_prompt"
    return "analyze_prompt"


def _after_analysis(state: AgentState) -> str:
    """After analysis: abort on fatal error, otherwise continue to scoring."""
    if _has_fatal_error(state):
        return END
    return "score_prompt"


def _after_scoring(state: AgentState) -> str:
    """After scoring: FULL -> run output first, STRUCTURE -> improve directly."""
    phase = state.get("eval_phase") or EvalPhase.STRUCTURE
    if phase == EvalPhase.FULL:
        return "run_prompt_for_output"
    return "generate_improvements"


def _after_output_runner(state: AgentState) -> str:
    """After output runner: abort on fatal error, otherwise evaluate output."""
    if _has_fatal_error(state):
        return END
    return "evaluate_output"


def _after_output_eval(state: AgentState) -> str:
    """After output eval: abort on error, FULL -> improve, OUTPUT -> report."""
    if _has_fatal_error(state):
        return END
    phase = state.get("eval_phase") or EvalPhase.STRUCTURE
    if phase == EvalPhase.OUTPUT:
        return "build_report"
    return "generate_improvements"


def _after_improvements(state: AgentState) -> str:
    """After improvements: abort on fatal error, route to optimized runner if rewritten prompt exists."""
    if _has_fatal_error(state):
        return END
    if state.get("rewritten_prompt"):
        return "run_optimized_prompt"
    # No rewritten prompt — skip optimized pipeline, go straight to meta
    return "meta_evaluate"


def _after_optimized_runner(state: AgentState) -> str:
    """After optimized runner: abort on fatal error, otherwise evaluate optimized output."""
    if _has_fatal_error(state):
        return END
    return "evaluate_optimized_output"


def _after_optimized_eval(state: AgentState) -> str:
    """After optimized output eval: abort on fatal error, otherwise meta-evaluate."""
    if _has_fatal_error(state):
        return END
    return "meta_evaluate"


def _after_meta_evaluate(state: AgentState) -> str:
    """After meta-evaluation: abort on fatal error, otherwise build report."""
    if _has_fatal_error(state):
        return END
    return "build_report"


def _should_continue(state: AgentState) -> str:
    """Determine whether to continue the conversation or end."""
    if state.get("should_continue", False):
        return "handle_followup"
    return END


def _route_followup(state: AgentState) -> str:
    """Route after follow-up: re_evaluate loops back, others end."""
    if state.get("followup_action") == "re_evaluate":
        return "route_input"
    return END


def build_graph() -> StateGraph:
    """Build and compile the prompt evaluator LangGraph.

    Graph topology (FULL mode):
        __start__ -> route_input
          |--[STRUCTURE]-> analyze -> score -> improve -> [optimized_runner?] -> [eval_optimized?] -> meta_evaluate -> build_report
          |
          |--[FULL]-> analyze -> score -> run_output -> eval_output -> improve -> [optimized_runner?] -> [eval_optimized?] -> meta_evaluate -> build_report
          |
          `--[OUTPUT]-> run_output -> eval_output -> build_report

        After improvements:
          - If rewritten_prompt exists -> run_optimized_prompt -> evaluate_optimized_output -> meta_evaluate
          - If no rewritten_prompt    -> meta_evaluate (directly)
        meta_evaluate -> build_report (always, unconditional)
        build_report -> should_continue?
          |-- handle_followup -> route_input (re_evaluate) / END
          `-- END
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("route_input", route_input)
    graph.add_node("analyze_prompt", analyze_prompt)
    graph.add_node("analyze_system_prompt", analyze_system_prompt)
    graph.add_node("score_prompt", score_prompt)
    graph.add_node("generate_improvements", generate_improvements)
    graph.add_node("run_prompt_for_output", run_prompt_for_output)
    graph.add_node("evaluate_output", evaluate_output)
    graph.add_node("run_optimized_prompt", run_optimized_prompt)
    graph.add_node("evaluate_optimized_output", evaluate_optimized_output)
    graph.add_node("meta_evaluate", meta_evaluate)
    graph.add_node("build_report", build_report)
    graph.add_node("handle_followup", handle_followup)

    # Entry point
    graph.set_entry_point("route_input")

    # Conditional routing: phase-based
    graph.add_conditional_edges(
        "route_input",
        _route_by_phase,
        {
            "analyze_prompt": "analyze_prompt",
            "analyze_system_prompt": "analyze_system_prompt",
            "run_prompt_for_output": "run_prompt_for_output",
        },
    )

    # Both analyzers -> conditional: abort on error, otherwise score
    graph.add_conditional_edges(
        "analyze_prompt",
        _after_analysis,
        {"score_prompt": "score_prompt", END: END},
    )
    graph.add_conditional_edges(
        "analyze_system_prompt",
        _after_analysis,
        {"score_prompt": "score_prompt", END: END},
    )

    # Scorer -> conditional: FULL -> output runner, STRUCTURE -> improver
    graph.add_conditional_edges(
        "score_prompt",
        _after_scoring,
        {
            "run_prompt_for_output": "run_prompt_for_output",
            "generate_improvements": "generate_improvements",
        },
    )

    # Output runner -> conditional: abort on error, otherwise evaluate
    graph.add_conditional_edges(
        "run_prompt_for_output",
        _after_output_runner,
        {"evaluate_output": "evaluate_output", END: END},
    )

    # Output evaluator -> conditional: abort on error, FULL -> improver, OUTPUT -> report
    graph.add_conditional_edges(
        "evaluate_output",
        _after_output_eval,
        {
            "generate_improvements": "generate_improvements",
            "build_report": "build_report",
            END: END,
        },
    )

    # Improver -> conditional: abort on error, route to optimized runner or meta
    graph.add_conditional_edges(
        "generate_improvements",
        _after_improvements,
        {
            "run_optimized_prompt": "run_optimized_prompt",
            "meta_evaluate": "meta_evaluate",
            END: END,
        },
    )

    # Optimized runner -> conditional: abort on error, otherwise evaluate optimized
    graph.add_conditional_edges(
        "run_optimized_prompt",
        _after_optimized_runner,
        {"evaluate_optimized_output": "evaluate_optimized_output", END: END},
    )

    # Optimized output evaluator -> conditional: abort on error, otherwise meta
    graph.add_conditional_edges(
        "evaluate_optimized_output",
        _after_optimized_eval,
        {"meta_evaluate": "meta_evaluate", END: END},
    )

    # Meta-evaluator -> conditional: abort on error, otherwise build report
    graph.add_conditional_edges(
        "meta_evaluate",
        _after_meta_evaluate,
        {"build_report": "build_report", END: END},
    )

    # Report -> conditional: continue or end
    graph.add_conditional_edges(
        "build_report",
        _should_continue,
        {
            "handle_followup": "handle_followup",
            END: END,
        },
    )

    # Follow-up: re_evaluate loops back, others end
    graph.add_conditional_edges(
        "handle_followup",
        _route_followup,
        {
            "route_input": "route_input",
            END: END,
        },
    )

    return graph.compile()


_graph_instance: StateGraph | None = None


def get_graph() -> StateGraph:
    """Return a lazily compiled singleton of the evaluator graph.

    Defers compilation until first use so that environment variables
    (loaded via ``load_dotenv`` / ``get_settings``) are available
    before any LangChain/LangGraph internals run.

    Returns:
        The compiled LangGraph StateGraph.
    """
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance
