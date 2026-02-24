"""Unit tests for Email Creation Prompts criteria and task type selection."""

from __future__ import annotations

from src.evaluator.criteria import (
    ALL_CRITERIA,
    EMAIL_CONSTRAINTS_CRITERIA,
    EMAIL_CONTEXT_CRITERIA,
    EMAIL_CRITERIA,
    EMAIL_REFERENCES_CRITERIA,
    EMAIL_TASK_CRITERIA,
    get_criteria_for_task_type,
)


class TestEmailCriteriaStructure:
    def test_email_task_has_four_criteria(self):
        assert len(EMAIL_TASK_CRITERIA) == 4

    def test_email_context_has_four_criteria(self):
        assert len(EMAIL_CONTEXT_CRITERIA) == 4

    def test_email_references_has_three_criteria(self):
        assert len(EMAIL_REFERENCES_CRITERIA) == 3

    def test_email_constraints_has_four_criteria(self):
        assert len(EMAIL_CONSTRAINTS_CRITERIA) == 4

    def test_email_criteria_dict_has_four_dimensions(self):
        assert set(EMAIL_CRITERIA.keys()) == {"task", "context", "references", "constraints"}


class TestEmailCriteriaWeights:
    def test_task_weights_sum_to_one(self):
        total = sum(c.weight for c in EMAIL_TASK_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_context_weights_sum_to_one(self):
        total = sum(c.weight for c in EMAIL_CONTEXT_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_references_weights_sum_to_one(self):
        total = sum(c.weight for c in EMAIL_REFERENCES_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_constraints_weights_sum_to_one(self):
        total = sum(c.weight for c in EMAIL_CONSTRAINTS_CRITERIA)
        assert abs(total - 1.0) < 0.01


class TestEmailCriteriaNames:
    def test_task_criteria_names(self):
        names = {c.name for c in EMAIL_TASK_CRITERIA}
        assert names == {
            "email_action_specified",
            "tone_style_defined",
            "email_purpose_clear",
            "email_structure_specified",
        }

    def test_context_criteria_names(self):
        names = {c.name for c in EMAIL_CONTEXT_CRITERIA}
        assert names == {
            "recipient_defined",
            "sender_context_provided",
            "situation_background",
            "relationship_dynamic",
        }

    def test_references_criteria_names(self):
        names = {c.name for c in EMAIL_REFERENCES_CRITERIA}
        assert names == {
            "email_examples_provided",
            "key_points_listed",
            "prior_thread_context",
        }

    def test_constraints_criteria_names(self):
        names = {c.name for c in EMAIL_CONSTRAINTS_CRITERIA}
        assert names == {
            "length_brevity",
            "formality_level",
            "content_exclusions",
            "call_to_action_specified",
        }


class TestGetCriteriaForTaskType:
    def test_general_returns_all_criteria(self):
        result = get_criteria_for_task_type("general")
        assert result is ALL_CRITERIA

    def test_email_writing_returns_email_criteria(self):
        result = get_criteria_for_task_type("email_writing")
        assert result is EMAIL_CRITERIA

    def test_unknown_type_returns_general(self):
        result = get_criteria_for_task_type("unknown")
        assert result is ALL_CRITERIA

    def test_empty_string_returns_general(self):
        result = get_criteria_for_task_type("")
        assert result is ALL_CRITERIA

    def test_email_criteria_differ_from_general(self):
        general = get_criteria_for_task_type("general")
        email = get_criteria_for_task_type("email_writing")
        # Same keys but different criteria objects
        assert set(general.keys()) == set(email.keys())
        assert general["task"] is not email["task"]
        assert general["context"] is not email["context"]


class TestEmailCriteriaHaveDetectionHints:
    def test_all_email_criteria_have_hints(self):
        for dim_name, criteria_list in EMAIL_CRITERIA.items():
            for criterion in criteria_list:
                assert criterion.detection_hint, (
                    f"Missing detection_hint for {dim_name}.{criterion.name}"
                )
                assert criterion.description, (
                    f"Missing description for {dim_name}.{criterion.name}"
                )
