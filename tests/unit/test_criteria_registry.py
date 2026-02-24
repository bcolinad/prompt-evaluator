"""Unit tests for the criteria registry."""

import pytest

from src.evaluator import TaskType
from src.evaluator.criteria import (
    _CRITERIA_REGISTRY,
    ALL_CRITERIA,
    Criterion,
    get_criteria_for_task_type,
)


class TestCriteriaRegistryCompleteness:
    """Verify all non-general TaskType values have criteria entries."""

    @pytest.mark.parametrize("task_type", [t for t in TaskType if t != TaskType.GENERAL])
    def test_task_type_in_criteria_registry(self, task_type: TaskType):
        assert task_type.value in _CRITERIA_REGISTRY, (
            f"{task_type.value} missing from _CRITERIA_REGISTRY"
        )


class TestGetCriteriaForTaskType:
    def test_general_returns_all_criteria(self):
        result = get_criteria_for_task_type("general")
        assert result is ALL_CRITERIA

    def test_unknown_type_returns_all_criteria(self):
        result = get_criteria_for_task_type("unknown_type")
        assert result is ALL_CRITERIA

    @pytest.mark.parametrize("key", list(_CRITERIA_REGISTRY.keys()))
    def test_known_type_returns_specific_criteria(self, key: str):
        result = get_criteria_for_task_type(key)
        assert result is _CRITERIA_REGISTRY[key]

    @pytest.mark.parametrize("key", list(_CRITERIA_REGISTRY.keys()))
    def test_criteria_dict_has_four_dimensions(self, key: str):
        criteria = _CRITERIA_REGISTRY[key]
        assert len(criteria) == 4, f"{key} has {len(criteria)} dimensions, expected 4"

    @pytest.mark.parametrize("key", list(_CRITERIA_REGISTRY.keys()))
    def test_criteria_values_are_criterion_lists(self, key: str):
        criteria = _CRITERIA_REGISTRY[key]
        for dim_name, crit_list in criteria.items():
            assert isinstance(crit_list, list), f"{key}.{dim_name} is not a list"
            for c in crit_list:
                assert isinstance(c, Criterion), f"{key}.{dim_name} contains non-Criterion"

    def test_all_criteria_has_four_dimensions(self):
        assert len(ALL_CRITERIA) == 4
