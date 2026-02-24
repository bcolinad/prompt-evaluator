"""Unit tests for evaluation Pydantic models."""

import pytest

from src.evaluator import (
    DimensionScore,
    EvalMode,
    EvaluationInput,
    Improvement,
    Priority,
    TCREIFlags,
)


class TestDimensionScore:
    def test_color_green_for_high_score(self):
        dim = DimensionScore(name="task", score=85, sub_criteria=[])
        assert dim.color == "#22C55E"

    def test_color_amber_for_medium_score(self):
        dim = DimensionScore(name="task", score=55, sub_criteria=[])
        assert dim.color == "#F59E0B"

    def test_color_red_for_low_score(self):
        dim = DimensionScore(name="task", score=20, sub_criteria=[])
        assert dim.color == "#EF4444"

    def test_score_boundaries(self):
        assert DimensionScore(name="test", score=0, sub_criteria=[]).color == "#EF4444"
        assert DimensionScore(name="test", score=100, sub_criteria=[]).color == "#22C55E"

    def test_invalid_score_raises(self):
        with pytest.raises(ValueError):
            DimensionScore(name="test", score=-1, sub_criteria=[])
        with pytest.raises(ValueError):
            DimensionScore(name="test", score=101, sub_criteria=[])


class TestEvaluationResult:
    def test_grade_color_mapping(self, sample_weak_result, sample_strong_result):
        assert sample_weak_result.grade_color == "#EF4444"
        assert sample_strong_result.grade_color == "#22C55E"

    def test_result_has_uuid(self, sample_weak_result):
        assert sample_weak_result.id is not None

    def test_result_has_timestamp(self, sample_weak_result):
        assert sample_weak_result.created_at is not None


class TestEvaluationInput:
    def test_default_mode_is_prompt(self):
        inp = EvaluationInput(text="test prompt")
        assert inp.mode == EvalMode.PROMPT

    def test_system_prompt_mode(self):
        inp = EvaluationInput(text="test", mode=EvalMode.SYSTEM_PROMPT, expected_outcome="SOAP notes")
        assert inp.mode == EvalMode.SYSTEM_PROMPT
        assert inp.expected_outcome == "SOAP notes"


class TestTCREIFlags:
    def test_default_all_false(self):
        flags = TCREIFlags()
        assert not flags.task
        assert not flags.context
        assert not flags.references
        assert not flags.evaluate
        assert not flags.iterate

    def test_partial_flags(self):
        flags = TCREIFlags(task=True, context=True)
        assert flags.task
        assert flags.context
        assert not flags.references


class TestImprovement:
    def test_priority_ordering(self):
        improvements = [
            Improvement(priority=Priority.LOW, title="Polish", suggestion="..."),
            Improvement(priority=Priority.CRITICAL, title="Fix task", suggestion="..."),
            Improvement(priority=Priority.HIGH, title="Add context", suggestion="..."),
        ]
        sorted_imps = sorted(improvements, key=lambda x: list(Priority).index(x.priority))
        assert sorted_imps[0].priority == Priority.CRITICAL
        assert sorted_imps[-1].priority == Priority.LOW
