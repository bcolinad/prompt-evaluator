"""Unit tests for the LangGraph workflow definition."""

from unittest.mock import patch

from langgraph.graph import END

from src.agent.graph import (
    _after_improvements,
    _after_meta_evaluate,
    _after_optimized_eval,
    _after_optimized_runner,
    _after_output_eval,
    _after_scoring,
    _route_by_phase,
    _route_followup,
    _should_continue,
    build_graph,
    get_graph,
)
from src.evaluator import EvalMode, EvalPhase


class TestRouteByPhase:
    def test_structure_routes_to_prompt_analyzer(self):
        state = {"eval_phase": EvalPhase.STRUCTURE, "mode": EvalMode.PROMPT}
        assert _route_by_phase(state) == "analyze_prompt"

    def test_structure_routes_to_system_prompt_analyzer(self):
        state = {"eval_phase": EvalPhase.STRUCTURE, "mode": EvalMode.SYSTEM_PROMPT}
        assert _route_by_phase(state) == "analyze_system_prompt"

    def test_full_routes_to_prompt_analyzer(self):
        state = {"eval_phase": EvalPhase.FULL, "mode": EvalMode.PROMPT}
        assert _route_by_phase(state) == "analyze_prompt"

    def test_output_routes_to_output_runner(self):
        state = {"eval_phase": EvalPhase.OUTPUT, "mode": EvalMode.PROMPT}
        assert _route_by_phase(state) == "run_prompt_for_output"

    def test_defaults_to_structure_when_missing(self):
        state = {"mode": EvalMode.PROMPT}
        assert _route_by_phase(state) == "analyze_prompt"


class TestAfterScoring:
    def test_full_goes_to_output_runner(self):
        state = {"eval_phase": EvalPhase.FULL}
        assert _after_scoring(state) == "run_prompt_for_output"

    def test_structure_goes_to_improvements(self):
        state = {"eval_phase": EvalPhase.STRUCTURE}
        assert _after_scoring(state) == "generate_improvements"

    def test_defaults_to_improvements_when_missing(self):
        state = {}
        assert _after_scoring(state) == "generate_improvements"


class TestAfterOutputEval:
    def test_full_goes_to_improvements(self):
        state = {"eval_phase": EvalPhase.FULL}
        assert _after_output_eval(state) == "generate_improvements"

    def test_output_goes_to_report(self):
        state = {"eval_phase": EvalPhase.OUTPUT}
        assert _after_output_eval(state) == "build_report"

    def test_defaults_to_improvements_when_missing(self):
        state = {}
        assert _after_output_eval(state) == "generate_improvements"


class TestShouldContinue:
    def test_continues_when_flag_true(self):
        state = {"should_continue": True}
        assert _should_continue(state) == "handle_followup"

    def test_ends_when_flag_false(self):
        state = {"should_continue": False}
        assert _should_continue(state) == END

    def test_ends_when_flag_missing(self):
        state = {}
        assert _should_continue(state) == END


class TestRouteFollowup:
    def test_re_evaluate_loops_back(self):
        state = {"followup_action": "re_evaluate"}
        assert _route_followup(state) == "route_input"

    def test_explain_ends(self):
        state = {"followup_action": "explain"}
        assert _route_followup(state) == END

    def test_adjust_rewrite_ends(self):
        state = {"followup_action": "adjust_rewrite"}
        assert _route_followup(state) == END

    def test_mode_switch_ends(self):
        state = {"followup_action": "mode_switch"}
        assert _route_followup(state) == END

    def test_no_action_ends(self):
        state = {}
        assert _route_followup(state) == END


class TestAfterImprovements:
    def test_rewritten_prompt_routes_to_optimized_runner(self):
        state = {"rewritten_prompt": "Improved version of the prompt"}
        assert _after_improvements(state) == "run_optimized_prompt"

    def test_no_rewritten_prompt_routes_to_meta_evaluate(self):
        state = {}
        assert _after_improvements(state) == "meta_evaluate"

    def test_empty_rewritten_prompt_routes_to_meta_evaluate(self):
        state = {"rewritten_prompt": ""}
        assert _after_improvements(state) == "meta_evaluate"

    def test_none_rewritten_prompt_routes_to_meta_evaluate(self):
        state = {"rewritten_prompt": None}
        assert _after_improvements(state) == "meta_evaluate"

    def test_fatal_error_routes_to_end(self):
        state = {"error_message": "Fatal: billing issue", "rewritten_prompt": "something"}
        assert _after_improvements(state) == END

    def test_fatal_error_without_rewritten_prompt_routes_to_end(self):
        state = {"error_message": "Fatal: unexpected failure"}
        assert _after_improvements(state) == END


class TestAfterOptimizedRunner:
    def test_no_error_routes_to_evaluate_optimized_output(self):
        state = {}
        assert _after_optimized_runner(state) == "evaluate_optimized_output"

    def test_fatal_error_routes_to_end(self):
        state = {"error_message": "Fatal: provider unavailable"}
        assert _after_optimized_runner(state) == END


class TestAfterOptimizedEval:
    def test_no_error_routes_to_meta_evaluate(self):
        state = {}
        assert _after_optimized_eval(state) == "meta_evaluate"

    def test_fatal_error_routes_to_end(self):
        state = {"error_message": "Fatal: evaluation crashed"}
        assert _after_optimized_eval(state) == END


class TestAfterMetaEvaluate:
    def test_no_error_routes_to_report(self):
        state = {}
        assert _after_meta_evaluate(state) == "build_report"

    def test_fatal_error_routes_to_end(self):
        state = {"error_message": "Fatal: auth error"}
        assert _after_meta_evaluate(state) == END


class TestBuildGraph:
    def test_graph_compiles(self):
        graph = build_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = build_graph()
        node_names = set(graph.get_graph().nodes.keys())
        expected = {
            "__start__",
            "__end__",
            "route_input",
            "analyze_prompt",
            "analyze_system_prompt",
            "score_prompt",
            "generate_improvements",
            "run_optimized_prompt",
            "evaluate_optimized_output",
            "meta_evaluate",
            "run_prompt_for_output",
            "evaluate_output",
            "build_report",
            "handle_followup",
        }
        assert expected.issubset(node_names)

    def test_graph_has_all_new_nodes(self):
        graph = build_graph()
        node_names = set(graph.get_graph().nodes.keys())
        assert "run_prompt_for_output" in node_names
        assert "evaluate_output" in node_names
        assert "build_report" in node_names
        assert "run_optimized_prompt" in node_names
        assert "evaluate_optimized_output" in node_names


class TestGetGraph:
    def test_get_graph_returns_compiled_graph(self):
        import src.agent.graph as graph_module

        graph_module._graph_instance = None
        graph = get_graph()
        assert graph is not None

    def test_get_graph_returns_singleton(self):
        import src.agent.graph as graph_module

        graph_module._graph_instance = None
        first = get_graph()
        second = get_graph()
        assert first is second

    def test_get_graph_reuses_existing_instance(self):
        import src.agent.graph as graph_module

        graph_module._graph_instance = None
        first = get_graph()
        with patch.object(graph_module, "build_graph") as mock_build:
            second = get_graph()
            mock_build.assert_not_called()
        assert first is second


class TestAgentStateFields:
    def test_task_type_declared_in_state(self):
        from src.agent.state import AgentState

        assert "task_type" in AgentState.__annotations__

    def test_prompt_type_declared_in_state(self):
        from src.agent.state import AgentState

        assert "prompt_type" in AgentState.__annotations__

    def test_task_type_preserved_in_state_dict(self):
        from src.evaluator import TaskType

        state = {
            "task_type": TaskType.EMAIL_WRITING,
            "prompt_type": "continuation",
        }
        assert state["task_type"] == TaskType.EMAIL_WRITING
        assert state["prompt_type"] == "continuation"

    def test_strategy_declared_in_state(self):
        from src.agent.state import AgentState

        assert "strategy" in AgentState.__annotations__

    def test_meta_assessment_declared_in_state(self):
        from src.agent.state import AgentState

        assert "meta_assessment" in AgentState.__annotations__

    def test_meta_findings_declared_in_state(self):
        from src.agent.state import AgentState

        assert "meta_findings" in AgentState.__annotations__

    def test_execution_count_declared_in_state(self):
        from src.agent.state import AgentState

        assert "execution_count" in AgentState.__annotations__

    def test_original_outputs_declared_in_state(self):
        from src.agent.state import AgentState

        assert "original_outputs" in AgentState.__annotations__

    def test_optimized_outputs_declared_in_state(self):
        from src.agent.state import AgentState

        assert "optimized_outputs" in AgentState.__annotations__

    def test_cot_reasoning_trace_declared_in_state(self):
        from src.agent.state import AgentState

        assert "cot_reasoning_trace" in AgentState.__annotations__

    def test_tot_branches_data_declared_in_state(self):
        from src.agent.state import AgentState

        assert "tot_branches_data" in AgentState.__annotations__

    def test_optimized_output_evaluation_declared_in_state(self):
        from src.agent.state import AgentState

        assert "optimized_output_evaluation" in AgentState.__annotations__

    def test_original_output_summary_declared_in_state(self):
        from src.agent.state import AgentState

        assert "original_output_summary" in AgentState.__annotations__

    def test_optimized_output_summary_declared_in_state(self):
        from src.agent.state import AgentState

        assert "optimized_output_summary" in AgentState.__annotations__
