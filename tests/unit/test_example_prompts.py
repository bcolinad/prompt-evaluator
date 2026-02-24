"""Unit tests for the example prompts data module."""

from __future__ import annotations

import pytest

from src.evaluator import TaskType
from src.evaluator.example_prompts import (
    EXAMPLE_PROMPTS,
    ExamplePrompt,
    get_example_for_task_type,
)


class TestExamplePromptsRegistry:
    def test_all_task_types_have_examples(self):
        for task_type in TaskType:
            assert task_type in EXAMPLE_PROMPTS, f"Missing example for {task_type}"

    def test_registry_has_exactly_six_entries(self):
        assert len(EXAMPLE_PROMPTS) == 6


class TestGetExampleForTaskType:
    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_returns_example_prompt_instance(self, task_type: TaskType):
        result = get_example_for_task_type(task_type)
        assert isinstance(result, ExamplePrompt)

    def test_general_returns_correct_example(self):
        result = get_example_for_task_type(TaskType.GENERAL)
        assert "veterinarian" in result.full_prompt.lower()

    def test_email_returns_correct_example(self):
        result = get_example_for_task_type(TaskType.EMAIL_WRITING)
        assert "email" in result.full_prompt.lower()

    def test_summarization_returns_correct_example(self):
        result = get_example_for_task_type(TaskType.SUMMARIZATION)
        assert "summarize" in result.full_prompt.lower()


class TestExamplePromptStructure:
    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_each_example_has_four_sections(self, task_type: TaskType):
        example = get_example_for_task_type(task_type)
        assert len(example.sections) == 4

    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_sections_cover_all_dimensions(self, task_type: TaskType):
        example = get_example_for_task_type(task_type)
        dimensions = {s.dimension for s in example.sections}
        assert dimensions == {"Task", "Context", "References", "Constraints"}

    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_all_fields_are_non_empty_strings(self, task_type: TaskType):
        example = get_example_for_task_type(task_type)
        assert example.title.strip()
        assert example.full_prompt.strip()
        assert example.overall_description.strip()

        for section in example.sections:
            assert section.dimension.strip()
            assert section.label.strip()
            assert section.text.strip()
            assert section.explanation.strip()

    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_estimated_score_in_valid_range(self, task_type: TaskType):
        example = get_example_for_task_type(task_type)
        assert 0 <= example.estimated_score <= 100

    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_estimated_score_is_high(self, task_type: TaskType):
        """Example prompts should demonstrate strong prompt structure."""
        example = get_example_for_task_type(task_type)
        assert example.estimated_score >= 80


class TestDataclassImmutability:
    def test_example_prompt_is_frozen(self):
        example = get_example_for_task_type(TaskType.GENERAL)
        with pytest.raises(AttributeError):
            example.title = "changed"  # type: ignore[misc]

    def test_annotated_section_is_frozen(self):
        example = get_example_for_task_type(TaskType.GENERAL)
        section = example.sections[0]
        with pytest.raises(AttributeError):
            section.dimension = "changed"  # type: ignore[misc]
