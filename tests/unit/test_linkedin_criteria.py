"""Unit tests for LinkedIn Professional Post Prompts criteria and task type selection."""

from __future__ import annotations

from src.evaluator.criteria import (
    LINKEDIN_CONSTRAINTS_CRITERIA,
    LINKEDIN_CONTEXT_CRITERIA,
    LINKEDIN_CRITERIA,
    LINKEDIN_REFERENCES_CRITERIA,
    LINKEDIN_TASK_CRITERIA,
    get_criteria_for_task_type,
)


class TestLinkedinCriteriaStructure:
    def test_linkedin_task_has_four_criteria(self):
        assert len(LINKEDIN_TASK_CRITERIA) == 4

    def test_linkedin_context_has_four_criteria(self):
        assert len(LINKEDIN_CONTEXT_CRITERIA) == 4

    def test_linkedin_references_has_three_criteria(self):
        assert len(LINKEDIN_REFERENCES_CRITERIA) == 3

    def test_linkedin_constraints_has_four_criteria(self):
        assert len(LINKEDIN_CONSTRAINTS_CRITERIA) == 4

    def test_linkedin_criteria_dict_has_four_dimensions(self):
        assert set(LINKEDIN_CRITERIA.keys()) == {"task", "context", "references", "constraints"}


class TestLinkedinCriteriaWeights:
    def test_task_weights_sum_to_one(self):
        total = sum(c.weight for c in LINKEDIN_TASK_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_context_weights_sum_to_one(self):
        total = sum(c.weight for c in LINKEDIN_CONTEXT_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_references_weights_sum_to_one(self):
        total = sum(c.weight for c in LINKEDIN_REFERENCES_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_constraints_weights_sum_to_one(self):
        total = sum(c.weight for c in LINKEDIN_CONSTRAINTS_CRITERIA)
        assert abs(total - 1.0) < 0.01


class TestLinkedinCriteriaNames:
    def test_task_criteria_names(self):
        names = {c.name for c in LINKEDIN_TASK_CRITERIA}
        assert names == {
            "post_objective_defined",
            "writing_voice_specified",
            "content_format_specified",
            "call_to_action_defined",
        }

    def test_context_criteria_names(self):
        names = {c.name for c in LINKEDIN_CONTEXT_CRITERIA}
        assert names == {
            "target_audience_specified",
            "author_identity_defined",
            "industry_topic_context",
            "platform_awareness",
        }

    def test_references_criteria_names(self):
        names = {c.name for c in LINKEDIN_REFERENCES_CRITERIA}
        assert names == {
            "inspiration_posts_provided",
            "data_statistics_referenced",
            "expertise_basis_specified",
        }

    def test_constraints_criteria_names(self):
        names = {c.name for c in LINKEDIN_CONSTRAINTS_CRITERIA}
        assert names == {
            "length_formatting_constraints",
            "tone_boundaries",
            "content_exclusions",
            "hashtag_mention_requirements",
        }


class TestLinkedinCriteriaRouting:
    def test_linkedin_post_returns_linkedin_criteria(self):
        result = get_criteria_for_task_type("linkedin_post")
        assert result is LINKEDIN_CRITERIA

    def test_linkedin_criteria_differ_from_general(self):
        general = get_criteria_for_task_type("general")
        linkedin = get_criteria_for_task_type("linkedin_post")
        assert set(general.keys()) == set(linkedin.keys())
        assert general["task"] is not linkedin["task"]
        assert general["context"] is not linkedin["context"]


class TestLinkedinCriteriaContent:
    def test_all_linkedin_criteria_have_hints(self):
        for dim_name, criteria_list in LINKEDIN_CRITERIA.items():
            for criterion in criteria_list:
                assert criterion.detection_hint, (
                    f"Missing detection_hint for {dim_name}.{criterion.name}"
                )
                assert criterion.description, (
                    f"Missing description for {dim_name}.{criterion.name}"
                )
