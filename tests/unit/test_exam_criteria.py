"""Unit tests for exam/interview evaluation criteria."""

from src.evaluator.criteria import (
    EXAM_CONSTRAINTS_CRITERIA,
    EXAM_CONTEXT_CRITERIA,
    EXAM_CRITERIA,
    EXAM_REFERENCES_CRITERIA,
    EXAM_TASK_CRITERIA,
    get_criteria_for_task_type,
)


class TestExamCriteriaStructure:
    """Verify criteria are correctly structured and registered."""

    def test_task_criteria_count(self) -> None:
        assert len(EXAM_TASK_CRITERIA) == 4

    def test_context_criteria_count(self) -> None:
        assert len(EXAM_CONTEXT_CRITERIA) == 4

    def test_references_criteria_count(self) -> None:
        assert len(EXAM_REFERENCES_CRITERIA) == 3

    def test_constraints_criteria_count(self) -> None:
        assert len(EXAM_CONSTRAINTS_CRITERIA) == 4

    def test_criteria_dict_has_four_dimensions(self) -> None:
        assert set(EXAM_CRITERIA.keys()) == {"task", "context", "references", "constraints"}

    def test_dispatcher_returns_exam_criteria(self) -> None:
        result = get_criteria_for_task_type("exam_interview")
        assert result is EXAM_CRITERIA


class TestExamCriteriaWeights:
    """Verify criterion weights sum to 1.0 within each dimension."""

    def test_task_weights_sum(self) -> None:
        total = sum(c.weight for c in EXAM_TASK_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_context_weights_sum(self) -> None:
        total = sum(c.weight for c in EXAM_CONTEXT_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_references_weights_sum(self) -> None:
        total = sum(c.weight for c in EXAM_REFERENCES_CRITERIA)
        assert abs(total - 1.0) < 0.01

    def test_constraints_weights_sum(self) -> None:
        total = sum(c.weight for c in EXAM_CONSTRAINTS_CRITERIA)
        assert abs(total - 1.0) < 0.01


class TestExamCriteriaNames:
    """Verify expected criterion names are present."""

    def test_task_criterion_names(self) -> None:
        names = {c.name for c in EXAM_TASK_CRITERIA}
        assert "assessment_objective_defined" in names
        assert "question_design_specified" in names
        assert "difficulty_calibration" in names
        assert "rubric_or_scoring_defined" in names

    def test_context_criterion_names(self) -> None:
        names = {c.name for c in EXAM_CONTEXT_CRITERIA}
        assert "candidate_profile_defined" in names
        assert "assessment_context_provided" in names
        assert "subject_domain_specified" in names
        assert "time_constraints_defined" in names

    def test_references_criterion_names(self) -> None:
        names = {c.name for c in EXAM_REFERENCES_CRITERIA}
        assert "sample_questions_provided" in names
        assert "source_material_referenced" in names
        assert "assessment_standards_referenced" in names

    def test_constraints_criterion_names(self) -> None:
        names = {c.name for c in EXAM_CONSTRAINTS_CRITERIA}
        assert "fairness_and_bias_safeguards" in names
        assert "anti_cheating_measures" in names
        assert "format_and_structure_constraints" in names
        assert "content_exclusions" in names


class TestExamCriteriaDetectionHints:
    """Verify detection hints contain relevant keywords."""

    def test_difficulty_hint_has_blooms(self) -> None:
        criterion = next(c for c in EXAM_TASK_CRITERIA if c.name == "difficulty_calibration")
        assert "Bloom" in criterion.detection_hint

    def test_fairness_hint_has_bias(self) -> None:
        criterion = next(c for c in EXAM_CONSTRAINTS_CRITERIA if c.name == "fairness_and_bias_safeguards")
        assert "bias" in criterion.detection_hint
