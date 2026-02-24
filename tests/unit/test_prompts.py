"""Unit tests for prompt templates."""

from src.prompts import (
    ANALYSIS_SYSTEM_PROMPT,
    FOLLOWUP_SYSTEM_PROMPT,
    IMPROVEMENT_SYSTEM_PROMPT,
    LINKEDIN_ANALYSIS_SYSTEM_PROMPT,
    LINKEDIN_IMPROVEMENT_GUIDANCE,
    LINKEDIN_OUTPUT_EVALUATION_SYSTEM_PROMPT,
    OUTPUT_EVALUATION_SYSTEM_PROMPT,
    SYSTEM_PROMPT_ANALYSIS_TEMPLATE,
)


class TestPromptTemplatesExist:
    def test_analysis_prompt_exists(self):
        assert ANALYSIS_SYSTEM_PROMPT is not None
        assert len(ANALYSIS_SYSTEM_PROMPT) > 100

    def test_system_prompt_analysis_exists(self):
        assert SYSTEM_PROMPT_ANALYSIS_TEMPLATE is not None
        assert len(SYSTEM_PROMPT_ANALYSIS_TEMPLATE) > 100

    def test_improvement_prompt_exists(self):
        assert IMPROVEMENT_SYSTEM_PROMPT is not None
        assert len(IMPROVEMENT_SYSTEM_PROMPT) > 50

    def test_followup_prompt_exists(self):
        assert FOLLOWUP_SYSTEM_PROMPT is not None
        assert len(FOLLOWUP_SYSTEM_PROMPT) > 100

    def test_output_evaluation_prompt_exists(self):
        assert OUTPUT_EVALUATION_SYSTEM_PROMPT is not None
        assert len(OUTPUT_EVALUATION_SYSTEM_PROMPT) > 100


class TestPromptPlaceholders:
    def test_analysis_has_criteria_placeholder(self):
        assert "{criteria}" in ANALYSIS_SYSTEM_PROMPT

    def test_analysis_has_rag_context_placeholder(self):
        assert "{rag_context}" in ANALYSIS_SYSTEM_PROMPT

    def test_system_analysis_has_criteria_placeholder(self):
        assert "{criteria}" in SYSTEM_PROMPT_ANALYSIS_TEMPLATE

    def test_system_analysis_has_rag_context_placeholder(self):
        assert "{rag_context}" in SYSTEM_PROMPT_ANALYSIS_TEMPLATE

    def test_improvement_has_rag_context_placeholder(self):
        assert "{rag_context}" in IMPROVEMENT_SYSTEM_PROMPT

    def test_followup_has_all_placeholders(self):
        assert "{overall_score}" in FOLLOWUP_SYSTEM_PROMPT
        assert "{grade}" in FOLLOWUP_SYSTEM_PROMPT
        assert "{dimension_summary}" in FOLLOWUP_SYSTEM_PROMPT
        assert "{improvements_summary}" in FOLLOWUP_SYSTEM_PROMPT
        assert "{rewritten_prompt}" in FOLLOWUP_SYSTEM_PROMPT
        assert "{original_prompt}" in FOLLOWUP_SYSTEM_PROMPT


class TestOutputEvaluationPrompt:
    def test_has_dimension_names(self):
        assert "relevance" in OUTPUT_EVALUATION_SYSTEM_PROMPT.lower()
        assert "coherence" in OUTPUT_EVALUATION_SYSTEM_PROMPT.lower()
        assert "completeness" in OUTPUT_EVALUATION_SYSTEM_PROMPT.lower()
        assert "instruction_following" in OUTPUT_EVALUATION_SYSTEM_PROMPT.lower()
        assert "hallucination_risk" in OUTPUT_EVALUATION_SYSTEM_PROMPT.lower()

    def test_mentions_langsmith(self):
        assert "LangSmith" in OUTPUT_EVALUATION_SYSTEM_PROMPT


class TestLinkedinPromptTemplates:
    def test_linkedin_analysis_prompt_exists(self):
        assert LINKEDIN_ANALYSIS_SYSTEM_PROMPT is not None
        assert len(LINKEDIN_ANALYSIS_SYSTEM_PROMPT) > 100

    def test_linkedin_analysis_has_criteria_placeholder(self):
        assert "{criteria}" in LINKEDIN_ANALYSIS_SYSTEM_PROMPT

    def test_linkedin_output_evaluation_has_dimension_names(self):
        prompt = LINKEDIN_OUTPUT_EVALUATION_SYSTEM_PROMPT.lower()
        assert "professional_tone_authenticity" in prompt
        assert "hook_scroll_stopping_power" in prompt
        assert "audience_engagement_potential" in prompt
        assert "value_delivery_expertise" in prompt
        assert "linkedin_platform_optimization" in prompt

    def test_linkedin_improvement_guidance_exists(self):
        assert LINKEDIN_IMPROVEMENT_GUIDANCE is not None
        assert len(LINKEDIN_IMPROVEMENT_GUIDANCE) > 50
