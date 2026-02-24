"""Unit tests for the example prompt Markdown formatter."""

from __future__ import annotations

import re

import pytest

from src.evaluator import TaskType
from src.evaluator.example_prompts import get_example_for_task_type
from src.utils.example_formatter import format_example_markdown


class TestFormatExampleMarkdown:
    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_output_contains_title(self, task_type: TaskType):
        example = get_example_for_task_type(task_type)
        result = format_example_markdown(example)
        assert f"**{example.title}**" in result

    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_output_contains_code_block(self, task_type: TaskType):
        example = get_example_for_task_type(task_type)
        result = format_example_markdown(example)
        assert "```" in result
        # Full prompt should appear inside the code block
        assert example.full_prompt in result

    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_output_contains_estimated_score(self, task_type: TaskType):
        example = get_example_for_task_type(task_type)
        result = format_example_markdown(example)
        assert f"**{example.estimated_score}/100**" in result

    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_output_contains_all_dimension_labels(self, task_type: TaskType):
        example = get_example_for_task_type(task_type)
        result = format_example_markdown(example)
        for section in example.sections:
            assert f"] {section.dimension}**: {section.label}" in result

    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_output_has_compact_dimension_lines(self, task_type: TaskType):
        """Each dimension should be a single bullet-point line."""
        example = get_example_for_task_type(task_type)
        result = format_example_markdown(example)
        dimension_lines = [line for line in result.splitlines() if line.startswith("- **[")]
        assert len(dimension_lines) == 4

    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_output_contains_no_html_tags(self, task_type: TaskType):
        example = get_example_for_task_type(task_type)
        result = format_example_markdown(example)
        # Check for common HTML tags
        html_pattern = re.compile(r"<(?:div|span|p|br|h[1-6]|ul|ol|li|a|img|table|tr|td)\b")
        assert not html_pattern.search(result), "Output should not contain HTML tags"

    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_output_ends_with_call_to_action(self, task_type: TaskType):
        example = get_example_for_task_type(task_type)
        result = format_example_markdown(example)
        assert result.strip().endswith("*Paste your own prompt below to see how it compares.*")

    def test_output_contains_dimension_prefixes(self):
        example = get_example_for_task_type(TaskType.GENERAL)
        result = format_example_markdown(example)
        assert "**[T] Task**" in result
        assert "**[C] Context**" in result
        assert "**[R] References**" in result
        assert "**[E/I] Constraints**" in result

    def test_output_is_string(self):
        example = get_example_for_task_type(TaskType.GENERAL)
        result = format_example_markdown(example)
        assert isinstance(result, str)
        assert len(result) > 50

    @pytest.mark.parametrize("task_type", list(TaskType))
    def test_output_does_not_contain_verbose_explanations(self, task_type: TaskType):
        """Compact format should NOT include italic explanation paragraphs."""
        example = get_example_for_task_type(task_type)
        result = format_example_markdown(example)
        # The old format had per-section explanations in italics
        # The compact format only has the final call-to-action in italics
        italic_lines = [
            line for line in result.splitlines()
            if line.startswith("*")
            and not line.startswith("**")
            and line.endswith("*")
            and len(line) > 5
        ]
        # Only the call-to-action line should be italic
        assert len(italic_lines) == 1
