"""Unit tests for Summarization Prompts criteria and task type selection."""

from __future__ import annotations

from src.evaluator.criteria import (
    SUMMARIZATION_CONSTRAINTS_CRITERIA,
    SUMMARIZATION_CONTEXT_CRITERIA,
    SUMMARIZATION_CRITERIA,
    SUMMARIZATION_REFERENCES_CRITERIA,
    SUMMARIZATION_TASK_CRITERIA,
    get_criteria_for_task_type,
)


class TestSummarizationCriteriaStructure:
    def test_summarization_task_has_four_criteria(self):
        assert len(SUMMARIZATION_TASK_CRITERIA) == 4

    def test_summarization_context_has_four_criteria(self):
        assert len(SUMMARIZATION_CONTEXT_CRITERIA) == 4

    def test_summarization_references_has_three_criteria(self):
        assert len(SUMMARIZATION_REFERENCES_CRITERIA) == 3

    def test_summarization_constraints_has_four_criteria(self):
        assert len(SUMMARIZATION_CONSTRAINTS_CRITERIA) == 4

    def test_summarization_criteria_dict_has_four_dimensions(self):
        assert set(SUMMARIZATION_CRITERIA.keys()) == {"task", "context", "references", "constraints"}


class TestSummarizationCriteriaWeights:
    def test_task_weights_sum_to_one(self):
        total = sum(c.weight for c in SUMMARIZATION_TASK_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_context_weights_sum_to_one(self):
        total = sum(c.weight for c in SUMMARIZATION_CONTEXT_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_references_weights_sum_to_one(self):
        total = sum(c.weight for c in SUMMARIZATION_REFERENCES_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_constraints_weights_sum_to_one(self):
        total = sum(c.weight for c in SUMMARIZATION_CONSTRAINTS_CRITERIA)
        assert abs(total - 1.0) < 0.01


class TestSummarizationCriteriaNames:
    def test_task_criteria_names(self):
        names = {c.name for c in SUMMARIZATION_TASK_CRITERIA}
        assert names == {
            "content_scope_specified",
            "format_and_tone_defined",
            "output_length_specified",
            "persona_or_reading_level",
        }

    def test_context_criteria_names(self):
        names = {c.name for c in SUMMARIZATION_CONTEXT_CRITERIA}
        assert names == {
            "source_document_described",
            "audience_for_summary",
            "summary_purpose",
            "domain_specificity",
        }

    def test_references_criteria_names(self):
        names = {c.name for c in SUMMARIZATION_REFERENCES_CRITERIA}
        assert names == {
            "source_material_provided",
            "example_summary_with_source",
            "key_sections_identified",
        }

    def test_constraints_criteria_names(self):
        names = {c.name for c in SUMMARIZATION_CONSTRAINTS_CRITERIA}
        assert names == {
            "length_word_limits",
            "inclusion_requirements",
            "hallucination_safeguards",
            "exclusion_constraints",
        }


class TestGetCriteriaForSummarization:
    def test_summarization_returns_summarization_criteria(self):
        result = get_criteria_for_task_type("summarization")
        assert result is SUMMARIZATION_CRITERIA

    def test_summarization_criteria_differ_from_general(self):
        general = get_criteria_for_task_type("general")
        summarization = get_criteria_for_task_type("summarization")
        assert set(general.keys()) == set(summarization.keys())
        assert general["task"] is not summarization["task"]
        assert general["context"] is not summarization["context"]

    def test_summarization_criteria_differ_from_email(self):
        email = get_criteria_for_task_type("email_writing")
        summarization = get_criteria_for_task_type("summarization")
        assert summarization["task"] is not email["task"]


class TestSummarizationCriteriaHaveDetectionHints:
    def test_all_summarization_criteria_have_hints(self):
        for dim_name, criteria_list in SUMMARIZATION_CRITERIA.items():
            for criterion in criteria_list:
                assert criterion.detection_hint, (
                    f"Missing detection_hint for {dim_name}.{criterion.name}"
                )
                assert criterion.description, (
                    f"Missing description for {dim_name}.{criterion.name}"
                )
