"""Unit tests for the professional audit report generator."""

from src.evaluator import (
    DimensionScore,
    EvalMode,
    EvalPhase,
    EvaluationResult,
    FullEvaluationReport,
    Grade,
    Improvement,
    OutputDimensionScore,
    OutputEvaluationResult,
    Priority,
    SubCriterionResult,
    TCREIFlags,
)
from src.utils.report_generator import (
    _quality_item,
    _tcrei_item,
    build_audit_data,
    generate_audit_report,
    generate_diff_html,
    generate_similarity_report,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_structure_result() -> EvaluationResult:
    return EvaluationResult(
        mode=EvalMode.PROMPT,
        input_text="Test prompt",
        overall_score=72,
        grade=Grade.GOOD,
        dimensions=[
            DimensionScore(
                name="task",
                score=85,
                sub_criteria=[
                    SubCriterionResult(name="action_verb", found=True, detail="Uses 'analyze'"),
                    SubCriterionResult(name="persona", found=False, detail="No persona defined"),
                ],
            ),
            DimensionScore(
                name="context",
                score=45,
                sub_criteria=[
                    SubCriterionResult(name="background", found=True, detail="Provides background"),
                    SubCriterionResult(name="audience", found=False, detail="No audience specified"),
                ],
            ),
        ],
        tcrei_flags=TCREIFlags(task=True, context=True),
        improvements=[
            Improvement(
                priority=Priority.HIGH,
                title="Improve Context",
                suggestion="Specify the target audience and environment.",
            ),
            Improvement(
                priority=Priority.MEDIUM,
                title="Add Constraints",
                suggestion="Add length and format constraints to the prompt.",
            ),
        ],
        rewritten_prompt="Improved prompt text here",
    )


def _make_output_result() -> OutputEvaluationResult:
    return OutputEvaluationResult(
        prompt_used="Test prompt",
        llm_output="Generated output",
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        dimensions=[
            OutputDimensionScore(name="relevance", score=0.92, comment="Highly relevant output"),
            OutputDimensionScore(name="coherence", score=0.88, comment="Well-structured response"),
            OutputDimensionScore(name="hallucination_risk", score=0.70, comment="Some inferred claims detected"),
        ],
        overall_score=0.83,
        grade=Grade.GOOD,
        langsmith_run_id="run-abc-123",
        findings=["Evaluated via Prompt Output Quality scoring.", "Good output."],
    )


def _make_full_report() -> FullEvaluationReport:
    return FullEvaluationReport(
        phase=EvalPhase.FULL,
        input_text="Test prompt",
        structure_result=_make_structure_result(),
        output_result=_make_output_result(),
        rewritten_prompt="Full report rewritten prompt",
    )


# ---------------------------------------------------------------------------
# _tcrei_item tests
# ---------------------------------------------------------------------------


class TestTcreiItem:
    def test_with_matching_improvement(self) -> None:
        dim = DimensionScore(
            name="context",
            score=45,
            sub_criteria=[
                SubCriterionResult(name="background", found=True, detail="Provides background"),
                SubCriterionResult(name="audience", found=False, detail="No audience"),
            ],
        )
        improvements = [
            Improvement(
                priority=Priority.HIGH,
                title="Improve Context",
                suggestion="Specify the target audience.",
            ),
        ]
        result = _tcrei_item(dim, improvements)

        assert result["label"] == "Context"
        assert result["score"] == 45
        assert "Provides background" in str(result["original"])
        assert "[HIGH]" in str(result["rec"])
        assert "Specify the target audience." in str(result["rec"])

    def test_without_improvement(self) -> None:
        dim = DimensionScore(
            name="task",
            score=95,
            sub_criteria=[
                SubCriterionResult(name="action_verb", found=True, detail="Clear verb 'analyze'"),
            ],
        )
        result = _tcrei_item(dim, [])

        assert result["label"] == "Task"
        assert result["score"] == 95
        assert result["rec"] == "No changes required."

    def test_no_found_sub_criteria(self) -> None:
        dim = DimensionScore(
            name="references",
            score=10,
            sub_criteria=[
                SubCriterionResult(name="examples", found=False, detail="No examples"),
            ],
        )
        result = _tcrei_item(dim, [])

        assert result["original"] == "No specific elements detected."

    def test_html_escaping_in_details(self) -> None:
        dim = DimensionScore(
            name="task",
            score=80,
            sub_criteria=[
                SubCriterionResult(
                    name="verb", found=True, detail='Uses <script>alert("xss")</script>'
                ),
            ],
        )
        result = _tcrei_item(dim, [])

        assert "<script>" not in str(result["original"])
        assert "&lt;script&gt;" in str(result["original"])


# ---------------------------------------------------------------------------
# _quality_item tests
# ---------------------------------------------------------------------------


class TestQualityItem:
    def test_high_score(self) -> None:
        dim = OutputDimensionScore(name="relevance", score=0.92, comment="Highly relevant")
        result = _quality_item(dim)

        assert result["name"] == "Relevance"
        assert result["value"] == 92
        assert result["issue"] == "None."
        assert result["fix"] == "Maintain current quality."

    def test_low_score(self) -> None:
        dim = OutputDimensionScore(
            name="hallucination_risk", score=0.70, comment="Some inferred claims"
        )
        result = _quality_item(dim)

        assert result["name"] == "Hallucination Risk"
        assert result["value"] == 70
        assert "Some inferred claims" in str(result["issue"])
        assert "above 85% threshold" in str(result["fix"])

    def test_boundary_score_85(self) -> None:
        dim = OutputDimensionScore(name="coherence", score=0.85, comment="Good structure")
        result = _quality_item(dim)

        assert result["issue"] == "None."
        assert result["fix"] == "Maintain current quality."

    def test_boundary_score_below_85(self) -> None:
        dim = OutputDimensionScore(name="coherence", score=0.84, comment="Minor issues")
        result = _quality_item(dim)

        assert result["issue"] != "None."

    def test_uses_recommendation_when_available(self) -> None:
        dim = OutputDimensionScore(
            name="completeness", score=0.60, comment="Missing sub-topics",
            recommendation="Add explicit sub-topic requirements to the prompt.",
        )
        result = _quality_item(dim)

        assert result["fix"] == "Add explicit sub-topic requirements to the prompt."
        assert "above 85% threshold" not in result["fix"]

    def test_falls_back_to_generic_when_no_recommendation(self) -> None:
        dim = OutputDimensionScore(
            name="completeness", score=0.60, comment="Missing sub-topics",
        )
        result = _quality_item(dim)

        assert "above 85% threshold" in result["fix"]

    def test_ignores_no_change_needed_recommendation(self) -> None:
        dim = OutputDimensionScore(
            name="completeness", score=0.60, comment="Missing sub-topics",
            recommendation="No change needed.",
        )
        result = _quality_item(dim)

        assert "above 85% threshold" in result["fix"]

    def test_html_escaping_in_comment(self) -> None:
        dim = OutputDimensionScore(
            name="test", score=0.50, comment='Contains <b>bold</b> & "quotes"'
        )
        result = _quality_item(dim)

        assert "<b>" not in str(result["desc"])
        assert "&lt;b&gt;" in str(result["desc"])


# ---------------------------------------------------------------------------
# build_audit_data tests
# ---------------------------------------------------------------------------


class TestBuildAuditData:
    def test_full_report(self) -> None:
        report = _make_full_report()
        data = build_audit_data(report)

        assert len(data["tcrei_data"]) == 2  # type: ignore[arg-type]
        assert len(data["quality_data"]) == 3  # type: ignore[arg-type]
        assert data["struct_score"] == 72
        assert data["struct_grade"] == "Good"
        assert data["output_score"] == 83
        assert data["output_grade"] == "Good"
        assert data["optimized_prompt"] == "Full report rewritten prompt"

    def test_structure_only(self) -> None:
        report = FullEvaluationReport(
            phase=EvalPhase.STRUCTURE,
            input_text="Test",
            structure_result=_make_structure_result(),
            output_result=None,
        )
        data = build_audit_data(report)

        assert len(data["tcrei_data"]) == 2  # type: ignore[arg-type]
        assert len(data["quality_data"]) == 0  # type: ignore[arg-type]
        assert data["output_score"] == 0
        assert data["output_grade"] == "N/A"
        # Falls back to structure rewritten prompt
        assert data["optimized_prompt"] == "Improved prompt text here"

    def test_output_only(self) -> None:
        report = FullEvaluationReport(
            phase=EvalPhase.OUTPUT,
            input_text="Test",
            structure_result=None,
            output_result=_make_output_result(),
        )
        data = build_audit_data(report)

        assert len(data["tcrei_data"]) == 0  # type: ignore[arg-type]
        assert len(data["quality_data"]) == 3  # type: ignore[arg-type]
        assert data["struct_score"] == 0
        assert data["struct_grade"] == "N/A"

    def test_empty_report(self) -> None:
        report = FullEvaluationReport(
            phase=EvalPhase.STRUCTURE,
            input_text="Test",
            structure_result=None,
            output_result=None,
        )
        data = build_audit_data(report)

        assert data["tcrei_data"] == []
        assert data["quality_data"] == []
        assert data["optimized_prompt"] == ""


# ---------------------------------------------------------------------------
# generate_audit_report tests
# ---------------------------------------------------------------------------


class TestGenerateAuditReport:
    def test_contains_json_data(self) -> None:
        report = _make_full_report()
        html = generate_audit_report(report)

        assert "const tcreiData =" in html
        assert "const qualityData =" in html
        assert '"label"' in html
        assert '"Task"' in html
        assert '"Context"' in html

    def test_contains_scores(self) -> None:
        report = _make_full_report()
        html = generate_audit_report(report)

        assert "72%" in html  # struct score
        assert "83%" in html  # output score
        assert "Good" in html  # grade

    def test_contains_optimized_prompt(self) -> None:
        report = _make_full_report()
        html = generate_audit_report(report)

        assert "Full report rewritten prompt" in html

    def test_xss_protection_script_tag(self) -> None:
        """Verify </script> is escaped — both via html.escape and JSON-level."""
        structure = _make_structure_result()
        structure.dimensions[0].sub_criteria[0] = SubCriterionResult(
            name="test", found=True, detail="payload</script><script>alert(1)"
        )
        report = FullEvaluationReport(
            phase=EvalPhase.FULL,
            input_text="Test",
            structure_result=structure,
            output_result=_make_output_result(),
        )
        result = generate_audit_report(report)

        # Extract the full tcreiData line (between "const tcreiData = " and the next "const")
        tcrei_block = result.split("const tcreiData =")[1].split("const qualityData")[0]
        # The raw </script> must NOT appear anywhere in the JSON payload
        assert "</script>" not in tcrei_block
        # html.escape() converts < to &lt; at data mapping time, preventing injection
        assert "&lt;/script&gt;" in tcrei_block

    def test_html_escaping_in_optimized_prompt(self) -> None:
        report = FullEvaluationReport(
            phase=EvalPhase.FULL,
            input_text="Test",
            structure_result=_make_structure_result(),
            output_result=_make_output_result(),
            rewritten_prompt='<img src=x onerror="alert(1)">',
        )
        html = generate_audit_report(report)

        assert '<img src=x onerror="alert(1)">' not in html
        assert "&lt;img" in html

    def test_template_structure_valid_html(self) -> None:
        report = _make_full_report()
        html = generate_audit_report(report)

        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html
        assert "Professional Prompt Shaper" in html
        assert "accordion-content" in html
        assert "grid-template-rows" in html

    def test_branding(self) -> None:
        report = _make_full_report()
        html = generate_audit_report(report)

        assert "Professional Prompt Shaper" in html
        assert "Professional Audit Report" in html

    def test_empty_dimensions_produce_empty_arrays(self) -> None:
        report = FullEvaluationReport(
            phase=EvalPhase.STRUCTURE,
            input_text="Test",
            structure_result=None,
            output_result=None,
        )
        html = generate_audit_report(report)

        assert "const tcreiData = []" in html
        assert "const qualityData = []" in html


# ---------------------------------------------------------------------------
# generate_similarity_report tests
# ---------------------------------------------------------------------------


class TestGenerateSimilarityReport:
    def test_full_data(self) -> None:
        eval_data = {
            "input_text": "Write a blog post about cats",
            "rewritten_prompt": "As a pet expert, write a detailed blog post...",
            "overall_score": 72,
            "grade": "Good",
            "output_score": 0.85,
            "improvements_summary": "Add more context about audience.",
        }
        result = generate_similarity_report(eval_data)

        assert "<!DOCTYPE html>" in result
        assert "72%" in result
        assert "Good" in result
        assert "85%" in result
        assert "Write a blog post about cats" in result
        assert "Add more context about audience." in result
        assert "As a pet expert, write a detailed blog post..." in result
        assert "copyPrompt()" in result

    def test_minimal_data_no_rewritten_no_output(self) -> None:
        eval_data = {
            "input_text": "Summarize this article",
            "overall_score": 45,
            "grade": "Needs Work",
        }
        result = generate_similarity_report(eval_data)

        assert "<!DOCTYPE html>" in result
        assert "45%" in result
        assert "Needs Work" in result
        assert "Summarize this article" in result
        # No optimized prompt block
        assert "Optimized Prompt" not in result
        # No output quality block
        assert "Output Quality" not in result

    def test_with_improvements_but_no_rewritten(self) -> None:
        eval_data = {
            "input_text": "Test prompt",
            "overall_score": 60,
            "grade": "Needs Work",
            "improvements_summary": "Specify the target audience.",
        }
        result = generate_similarity_report(eval_data)

        assert "Improvements" in result
        assert "Specify the target audience." in result
        assert "Optimized Prompt" not in result

    def test_html_escaping_in_prompt(self) -> None:
        eval_data = {
            "input_text": '<script>alert("xss")</script>',
            "rewritten_prompt": '<img src=x onerror="alert(1)">',
            "overall_score": 50,
            "grade": "Needs Work",
        }
        result = generate_similarity_report(eval_data)

        assert "<script>alert" not in result
        assert "&lt;script&gt;" in result
        assert '<img src=x onerror' not in result
        assert "&lt;img" in result

    def test_grade_color_excellent(self) -> None:
        eval_data = {
            "input_text": "Great prompt",
            "overall_score": 90,
            "grade": "Excellent",
        }
        result = generate_similarity_report(eval_data)
        assert "text-emerald-400" in result

    def test_grade_color_weak(self) -> None:
        eval_data = {
            "input_text": "Bad prompt",
            "overall_score": 20,
            "grade": "Weak",
        }
        result = generate_similarity_report(eval_data)
        assert "text-red-400" in result

    def test_valid_html_structure(self) -> None:
        eval_data = {
            "input_text": "Test",
            "overall_score": 72,
            "grade": "Good",
            "rewritten_prompt": "Better test",
        }
        result = generate_similarity_report(eval_data)

        assert result.startswith("<!DOCTYPE html>")
        assert "</html>" in result
        assert "Professional Prompt Shaper" in result


# ---------------------------------------------------------------------------
# generate_diff_html tests
# ---------------------------------------------------------------------------


class TestGenerateDiffHtml:
    def test_identical_texts(self) -> None:
        result = generate_diff_html("hello world", "hello world")
        assert "hello world" in result
        assert "line-through" not in result
        assert "#16a34a" not in result

    def test_empty_original(self) -> None:
        assert generate_diff_html("", "some text") == ""

    def test_empty_rewritten(self) -> None:
        assert generate_diff_html("some text", "") == ""

    def test_both_empty(self) -> None:
        assert generate_diff_html("", "") == ""

    def test_word_addition(self) -> None:
        result = generate_diff_html("hello world", "hello beautiful world")
        assert "#16a34a" in result  # green for addition
        assert "beautiful" in result

    def test_word_deletion(self) -> None:
        result = generate_diff_html("hello beautiful world", "hello world")
        assert "line-through" in result
        assert "beautiful" in result

    def test_word_replacement(self) -> None:
        result = generate_diff_html("hello world", "hello universe")
        assert "line-through" in result  # red for old
        assert "#16a34a" in result  # green for new
        assert "world" in result
        assert "universe" in result

    def test_html_escaping(self) -> None:
        result = generate_diff_html(
            '<script>alert("xss")</script>',
            "safe text",
        )
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_diff_in_audit_report(self) -> None:
        report = _make_full_report()
        html_output = generate_audit_report(report)
        assert "Prompt Comparison" in html_output
        assert "Word-Level Diff" in html_output

    def test_no_diff_section_when_no_rewritten(self) -> None:
        structure = _make_structure_result()
        structure.rewritten_prompt = None
        report = FullEvaluationReport(
            phase=EvalPhase.FULL,
            input_text="Test prompt",
            structure_result=structure,
            output_result=_make_output_result(),
            rewritten_prompt=None,
        )
        html_output = generate_audit_report(report)
        assert "Prompt Comparison" not in html_output

    def test_build_audit_data_includes_diff_html(self) -> None:
        report = _make_full_report()
        data = build_audit_data(report)
        assert "diff_html" in data
        assert data["diff_html"] != ""
