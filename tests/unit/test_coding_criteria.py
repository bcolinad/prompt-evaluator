"""Unit tests for coding task evaluation criteria."""

from src.evaluator.criteria import (
    CODING_CONSTRAINTS_CRITERIA,
    CODING_CONTEXT_CRITERIA,
    CODING_CRITERIA,
    CODING_REFERENCES_CRITERIA,
    CODING_TASK_CRITERIA,
    get_criteria_for_task_type,
)


class TestCodingCriteriaStructure:
    """Verify criteria are correctly structured and registered."""

    def test_task_criteria_count(self) -> None:
        assert len(CODING_TASK_CRITERIA) == 4

    def test_context_criteria_count(self) -> None:
        assert len(CODING_CONTEXT_CRITERIA) == 4

    def test_references_criteria_count(self) -> None:
        assert len(CODING_REFERENCES_CRITERIA) == 3

    def test_constraints_criteria_count(self) -> None:
        assert len(CODING_CONSTRAINTS_CRITERIA) == 4

    def test_criteria_dict_has_four_dimensions(self) -> None:
        assert set(CODING_CRITERIA.keys()) == {"task", "context", "references", "constraints"}

    def test_dispatcher_returns_coding_criteria(self) -> None:
        result = get_criteria_for_task_type("coding_task")
        assert result is CODING_CRITERIA


class TestCodingCriteriaWeights:
    """Verify criterion weights sum to 1.0 within each dimension."""

    def test_task_weights_sum(self) -> None:
        total = sum(c.weight for c in CODING_TASK_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_context_weights_sum(self) -> None:
        total = sum(c.weight for c in CODING_CONTEXT_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_references_weights_sum(self) -> None:
        total = sum(c.weight for c in CODING_REFERENCES_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_constraints_weights_sum(self) -> None:
        total = sum(c.weight for c in CODING_CONSTRAINTS_CRITERIA)
        assert abs(total - 1.0) < 0.01


class TestCodingCriteriaNames:
    """Verify expected criterion names are present."""

    def test_task_criterion_names(self) -> None:
        names = {c.name for c in CODING_TASK_CRITERIA}
        assert "programming_language_specified" in names
        assert "requirements_clarity" in names
        assert "architecture_guidance" in names
        assert "code_quality_standards" in names

    def test_context_criterion_names(self) -> None:
        names = {c.name for c in CODING_CONTEXT_CRITERIA}
        assert "project_context_provided" in names
        assert "technical_constraints_specified" in names
        assert "target_developer_audience" in names
        assert "existing_codebase_context" in names

    def test_references_criterion_names(self) -> None:
        names = {c.name for c in CODING_REFERENCES_CRITERIA}
        assert "code_examples_provided" in names
        assert "api_documentation_referenced" in names
        assert "test_expectations_defined" in names

    def test_constraints_criterion_names(self) -> None:
        names = {c.name for c in CODING_CONSTRAINTS_CRITERIA}
        assert "error_handling_requirements" in names
        assert "security_considerations" in names
        assert "performance_requirements" in names
        assert "scope_exclusions" in names


class TestCodingCriteriaDetectionHints:
    """Verify detection hints contain relevant keywords."""

    def test_language_hint_has_python(self) -> None:
        criterion = next(c for c in CODING_TASK_CRITERIA if c.name == "programming_language_specified")
        assert "Python" in criterion.detection_hint

    def test_security_hint_has_sql_injection(self) -> None:
        criterion = next(c for c in CODING_CONSTRAINTS_CRITERIA if c.name == "security_considerations")
        assert "SQL injection" in criterion.detection_hint
