"""Unit tests for LLM response schemas."""

import pytest

from src.evaluator.llm_schemas import (
    AnalysisLLMResponse,
    DimensionLLMResponse,
    FollowupLLMResponse,
    ImprovementLLMResponse,
    ImprovementsLLMResponse,
    OutputDimensionLLMResponse,
    OutputEvaluationLLMResponse,
    SubCriterionLLMResponse,
    TCREIFlagsLLMResponse,
)


class TestAnalysisLLMResponse:
    def test_defaults(self):
        resp = AnalysisLLMResponse()
        assert resp.dimensions == {}
        assert resp.tcrei_flags.task is False

    def test_full_construction(self):
        resp = AnalysisLLMResponse(
            dimensions={
                "task": DimensionLLMResponse(
                    score=75,
                    sub_criteria=[
                        SubCriterionLLMResponse(name="clear_action_verb", found=True, detail="Found 'Write'"),
                    ],
                ),
            },
            tcrei_flags=TCREIFlagsLLMResponse(task=True, context=False),
        )
        assert resp.dimensions["task"].score == 75
        assert resp.dimensions["task"].sub_criteria[0].found is True
        assert resp.tcrei_flags.task is True
        assert resp.tcrei_flags.context is False

    def test_model_validate_from_dict(self):
        data = {
            "dimensions": {
                "task": {"score": 80, "sub_criteria": [{"name": "test", "found": True, "detail": "ok"}]},
                "context": {"score": 50, "sub_criteria": []},
            },
            "tcrei_flags": {"task": True, "context": False, "references": False, "evaluate": False, "iterate": False},
        }
        resp = AnalysisLLMResponse.model_validate(data)
        assert resp.dimensions["task"].score == 80
        assert len(resp.dimensions["task"].sub_criteria) == 1

    def test_score_validation(self):
        with pytest.raises(Exception):
            DimensionLLMResponse(score=150, sub_criteria=[])

    def test_sub_criterion_defaults(self):
        sc = SubCriterionLLMResponse()
        assert sc.name == ""
        assert sc.found is False
        assert sc.detail == ""


class TestImprovementsLLMResponse:
    def test_defaults(self):
        resp = ImprovementsLLMResponse()
        assert resp.improvements == []
        assert resp.rewritten_prompt is None

    def test_full_construction(self):
        resp = ImprovementsLLMResponse(
            improvements=[
                ImprovementLLMResponse(priority="CRITICAL", title="Add task", suggestion="Be specific"),
                ImprovementLLMResponse(priority="LOW", title="Polish", suggestion="Minor edits"),
            ],
            rewritten_prompt="Improved prompt here",
        )
        assert len(resp.improvements) == 2
        assert resp.improvements[0].priority == "CRITICAL"
        assert resp.rewritten_prompt == "Improved prompt here"

    def test_model_validate_from_dict(self):
        data = {
            "improvements": [{"priority": "HIGH", "title": "A", "suggestion": "B"}],
            "rewritten_prompt": "New prompt",
        }
        resp = ImprovementsLLMResponse.model_validate(data)
        assert len(resp.improvements) == 1
        assert resp.rewritten_prompt == "New prompt"


class TestOutputEvaluationLLMResponse:
    def test_defaults(self):
        resp = OutputEvaluationLLMResponse()
        assert resp.dimensions == []
        assert resp.overall_score == 0.0
        assert resp.findings == []

    def test_full_construction(self):
        resp = OutputEvaluationLLMResponse(
            dimensions=[
                OutputDimensionLLMResponse(name="relevance", score=0.85, comment="Good"),
            ],
            overall_score=0.85,
            findings=["Finding 1"],
        )
        assert len(resp.dimensions) == 1
        assert resp.overall_score == 0.85

    def test_score_validation(self):
        with pytest.raises(Exception):
            OutputDimensionLLMResponse(name="test", score=1.5, comment="bad")

    def test_recommendation_default(self):
        dim = OutputDimensionLLMResponse(name="relevance", score=0.85, comment="Good")
        assert dim.recommendation == ""

    def test_recommendation_set(self):
        dim = OutputDimensionLLMResponse(
            name="completeness", score=0.60, comment="Missing points",
            recommendation="Add explicit requirements for sub-topics.",
        )
        assert dim.recommendation == "Add explicit requirements for sub-topics."

    def test_model_validate_with_recommendation(self):
        data = {
            "dimensions": [
                {"name": "relevance", "score": 0.85, "comment": "Good", "recommendation": "No change needed."},
            ],
            "overall_score": 0.85,
            "findings": ["Finding 1"],
        }
        resp = OutputEvaluationLLMResponse.model_validate(data)
        assert resp.dimensions[0].recommendation == "No change needed."

    def test_model_validate_without_recommendation(self):
        data = {
            "dimensions": [
                {"name": "relevance", "score": 0.85, "comment": "Good"},
            ],
            "overall_score": 0.85,
            "findings": [],
        }
        resp = OutputEvaluationLLMResponse.model_validate(data)
        assert resp.dimensions[0].recommendation == ""


class TestFollowupLLMResponse:
    def test_defaults(self):
        resp = FollowupLLMResponse()
        assert resp.intent == "explain"
        assert resp.response == ""
        assert resp.new_prompt is None
        assert resp.new_rewrite is None
        assert resp.new_mode is None

    def test_full_construction(self):
        resp = FollowupLLMResponse(
            intent="adjust_rewrite",
            response="Here is the adjusted version",
            new_rewrite="Better prompt",
        )
        assert resp.intent == "adjust_rewrite"
        assert resp.new_rewrite == "Better prompt"
        assert resp.new_prompt is None

    def test_model_validate_from_dict(self):
        data = {
            "intent": "re_evaluate",
            "response": "Re-evaluating",
            "new_prompt": "New prompt",
            "new_rewrite": None,
            "new_mode": None,
        }
        resp = FollowupLLMResponse.model_validate(data)
        assert resp.intent == "re_evaluate"
        assert resp.new_prompt == "New prompt"
