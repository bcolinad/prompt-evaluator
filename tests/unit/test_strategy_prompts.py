"""Unit tests for strategy prompt templates."""

from src.prompts.strategies import (
    COT_ANALYSIS_PREAMBLE,
    META_EVALUATION_PROMPT,
    TOT_BRANCH_GENERATION_PROMPT,
    TOT_BRANCH_SELECTION_PROMPT,
)


class TestCoTPrompt:
    def test_non_empty(self):
        assert len(COT_ANALYSIS_PREAMBLE) > 0

    def test_contains_step_markers(self):
        for step_num in range(1, 6):
            assert f"STEP {step_num}" in COT_ANALYSIS_PREAMBLE

    def test_contains_dimension_names(self):
        assert "TASK" in COT_ANALYSIS_PREAMBLE
        assert "CONTEXT" in COT_ANALYSIS_PREAMBLE
        assert "REFERENCES" in COT_ANALYSIS_PREAMBLE
        assert "CONSTRAINTS" in COT_ANALYSIS_PREAMBLE
        assert "TCREI" in COT_ANALYSIS_PREAMBLE


class TestToTPrompts:
    def test_branch_generation_non_empty(self):
        assert len(TOT_BRANCH_GENERATION_PROMPT) > 0

    def test_branch_generation_has_num_branches_placeholder(self):
        assert "{num_branches}" in TOT_BRANCH_GENERATION_PROMPT

    def test_branch_generation_has_input_placeholders(self):
        assert "{input_text}" in TOT_BRANCH_GENERATION_PROMPT
        assert "{analysis_summary}" in TOT_BRANCH_GENERATION_PROMPT
        assert "{overall_score}" in TOT_BRANCH_GENERATION_PROMPT
        assert "{grade}" in TOT_BRANCH_GENERATION_PROMPT

    def test_branch_selection_non_empty(self):
        assert len(TOT_BRANCH_SELECTION_PROMPT) > 0

    def test_branch_selection_has_num_branches_placeholder(self):
        assert "{num_branches}" in TOT_BRANCH_SELECTION_PROMPT

    def test_branch_selection_has_branches_text_placeholder(self):
        assert "{branches_text}" in TOT_BRANCH_SELECTION_PROMPT


class TestMetaPrompt:
    def test_non_empty(self):
        assert len(META_EVALUATION_PROMPT) > 0

    def test_contains_assessment_fields(self):
        assert "accuracy_score" in META_EVALUATION_PROMPT
        assert "completeness_score" in META_EVALUATION_PROMPT
        assert "actionability_score" in META_EVALUATION_PROMPT
        assert "faithfulness_score" in META_EVALUATION_PROMPT
        assert "overall_confidence" in META_EVALUATION_PROMPT

    def test_contains_input_placeholders(self):
        assert "{input_text}" in META_EVALUATION_PROMPT
        assert "{overall_score}" in META_EVALUATION_PROMPT
        assert "{grade}" in META_EVALUATION_PROMPT
        assert "{improvements_text}" in META_EVALUATION_PROMPT
        assert "{rewritten_prompt}" in META_EVALUATION_PROMPT

    def test_contains_refined_fields(self):
        assert "refined_improvements" in META_EVALUATION_PROMPT
        assert "refined_rewritten_prompt" in META_EVALUATION_PROMPT
        assert "meta_findings" in META_EVALUATION_PROMPT
