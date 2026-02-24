"""Unit tests for evaluation criteria definitions."""

from src.evaluator.criteria import (
    ALL_CRITERIA,
    CONSTRAINTS_CRITERIA,
    CONTEXT_CRITERIA,
    REFERENCES_CRITERIA,
    TASK_CRITERIA,
)


class TestCriteriaDefinitions:
    def test_all_dimensions_present(self):
        assert "task" in ALL_CRITERIA
        assert "context" in ALL_CRITERIA
        assert "references" in ALL_CRITERIA
        assert "constraints" in ALL_CRITERIA

    def test_task_has_four_criteria(self):
        assert len(TASK_CRITERIA) == 4

    def test_context_has_four_criteria(self):
        assert len(CONTEXT_CRITERIA) == 4

    def test_references_has_three_criteria(self):
        assert len(REFERENCES_CRITERIA) == 3

    def test_constraints_has_four_criteria(self):
        assert len(CONSTRAINTS_CRITERIA) == 4

    def test_all_criteria_have_names(self):
        for dimension, criteria in ALL_CRITERIA.items():
            for c in criteria:
                assert c.name, f"Criterion in {dimension} missing name"
                assert c.description, f"Criterion {c.name} missing description"
                assert c.detection_hint, f"Criterion {c.name} missing detection_hint"

    def test_weights_sum_to_one_per_dimension(self):
        for dimension, criteria in ALL_CRITERIA.items():
            total = sum(c.weight for c in criteria)
            assert abs(total - 1.0) < 0.01, f"{dimension} weights sum to {total}, expected ~1.0"

    def test_criteria_names_are_unique_per_dimension(self):
        for dimension, criteria in ALL_CRITERIA.items():
            names = [c.name for c in criteria]
            assert len(names) == len(set(names)), f"Duplicate criterion names in {dimension}"
