"""Unit tests for the centralized prompt registry."""

import pytest

from src.evaluator import TaskType
from src.prompts.registry import _REGISTRY, TaskTypePrompts, get_prompts_for_task_type


class TestRegistryCompleteness:
    """Every TaskType enum value (except GENERAL handled as default) has a registry entry."""

    @pytest.mark.parametrize("task_type", [t for t in TaskType if t != TaskType.GENERAL])
    def test_non_general_task_types_in_registry(self, task_type: TaskType):
        assert task_type.value in _REGISTRY, f"{task_type.value} missing from _REGISTRY"

    def test_general_in_registry(self):
        assert "general" in _REGISTRY


class TestRegistryFields:
    """All entries have non-empty analysis and output_evaluation prompts."""

    @pytest.mark.parametrize("key", list(_REGISTRY.keys()))
    def test_analysis_prompt_non_empty(self, key: str):
        prompts = _REGISTRY[key]
        assert isinstance(prompts.analysis, str)
        assert len(prompts.analysis) > 50

    @pytest.mark.parametrize("key", list(_REGISTRY.keys()))
    def test_output_evaluation_prompt_non_empty(self, key: str):
        prompts = _REGISTRY[key]
        assert isinstance(prompts.output_evaluation, str)
        assert len(prompts.output_evaluation) > 50

    @pytest.mark.parametrize("key", list(_REGISTRY.keys()))
    def test_fallback_dimensions_are_tuples(self, key: str):
        prompts = _REGISTRY[key]
        assert isinstance(prompts.fallback_dimensions, tuple)
        for name, comment in prompts.fallback_dimensions:
            assert isinstance(name, str)
            assert isinstance(comment, str)


class TestGetPromptsForTaskType:
    def test_returns_general_for_unknown_type(self):
        result = get_prompts_for_task_type("nonexistent_type")
        assert result is _REGISTRY["general"]

    def test_returns_correct_entry_for_known_type(self):
        result = get_prompts_for_task_type("email_writing")
        assert result is _REGISTRY["email_writing"]

    def test_general_has_empty_improvement_guidance(self):
        result = get_prompts_for_task_type("general")
        assert result.improvement_guidance == ""

    @pytest.mark.parametrize("key", [k for k in _REGISTRY if k != "general"])
    def test_non_general_has_improvement_guidance(self, key: str):
        result = get_prompts_for_task_type(key)
        assert len(result.improvement_guidance) > 0

    def test_returns_task_type_prompts_instance(self):
        result = get_prompts_for_task_type("general")
        assert isinstance(result, TaskTypePrompts)

    def test_fallback_dimensions_have_five_entries(self):
        for key, prompts in _REGISTRY.items():
            assert len(prompts.fallback_dimensions) == 5, (
                f"{key} has {len(prompts.fallback_dimensions)} fallback dimensions, expected 5"
            )
