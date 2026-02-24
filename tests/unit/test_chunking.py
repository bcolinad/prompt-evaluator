"""Unit tests for adaptive chunking utilities."""

from src.evaluator import DimensionScore, SubCriterionResult, TCREIFlags
from src.utils.chunking import (
    ChunkType,
    PromptChunk,
    aggregate_dimension_scores,
    chunk_prompt,
    detect_sections,
    should_chunk,
)


class TestShouldChunk:
    def test_short_text_returns_false(self):
        assert should_chunk("Write a blog post about dogs") is False

    def test_long_text_returns_true(self):
        # 2000 tokens * 4 chars/token = 8000 chars
        long_text = "word " * 2000
        assert should_chunk(long_text) is True

    def test_exactly_at_threshold(self):
        # 2000 tokens = 8000 chars
        text = "x" * 8000
        assert should_chunk(text) is True

    def test_just_below_threshold(self):
        text = "x" * 7999
        assert should_chunk(text) is False

    def test_empty_text(self):
        assert should_chunk("") is False

    def test_custom_threshold(self):
        text = "x" * 100  # 25 tokens
        assert should_chunk(text, threshold=20) is True
        assert should_chunk(text, threshold=30) is False


class TestDetectSections:
    def test_markdown_headers(self):
        text = "# Task\nDo something\n\n## Context\nBackground info"
        sections = detect_sections(text)
        assert len(sections) >= 2
        # First section should be task-related
        types = [s[1] for s in sections]
        assert ChunkType.TASK in types

    def test_xml_tags(self):
        text = "<task>Write a blog</task>\n<context>For developers</context>"
        sections = detect_sections(text)
        assert len(sections) >= 2
        types = [s[1] for s in sections]
        assert ChunkType.TASK in types
        assert ChunkType.CONTEXT in types

    def test_mixed_format(self):
        text = "# Task\nSomething\n\n<example>Like this</example>"
        sections = detect_sections(text)
        assert len(sections) >= 2

    def test_no_sections(self):
        text = "Write me a blog post about dogs. Keep it short."
        sections = detect_sections(text)
        assert len(sections) == 0

    def test_sorted_by_offset(self):
        text = "## Context\nInfo\n\n# Task\nDo something"
        sections = detect_sections(text)
        offsets = [s[0] for s in sections]
        assert offsets == sorted(offsets)

    def test_constraint_header(self):
        text = "### Constraints\nKeep it under 500 words"
        sections = detect_sections(text)
        types = [s[1] for s in sections]
        assert ChunkType.CONSTRAINTS in types

    def test_reference_header(self):
        text = "## References\nSee the following examples"
        sections = detect_sections(text)
        types = [s[1] for s in sections]
        assert ChunkType.EXAMPLES in types


class TestChunkPrompt:
    def test_empty_text_returns_empty(self):
        assert chunk_prompt("") == []

    def test_short_text_returns_single_chunk(self):
        text = "Write a blog post about dogs"
        chunks = chunk_prompt(text)
        assert len(chunks) >= 1
        assert chunks[0].content == text

    def test_markdown_sections_create_chunks(self):
        text = (
            "# Task\n"
            "Write a blog post about machine learning for beginners.\n\n"
            "## Context\n"
            "This is for a university course. Students have no prior experience.\n\n"
            "### Constraints\n"
            "Keep it under 500 words. Use simple language."
        )
        chunks = chunk_prompt(text)
        assert len(chunks) >= 2  # At least 2 sections after potential merging

    def test_paragraph_fallback(self):
        text = (
            "First paragraph about the task.\n\n"
            "Second paragraph about context.\n\n"
            "Third paragraph about constraints."
        )
        chunks = chunk_prompt(text)
        # Paragraphs will be created but may be merged if too small
        assert len(chunks) >= 1

    def test_xml_sections_create_chunks(self):
        text = (
            "<task>Write a blog post about dogs</task>\n\n"
            "<context>For pet owners new to dog ownership</context>\n\n"
            "<example>Here is a sample blog post...</example>"
        )
        chunks = chunk_prompt(text)
        assert len(chunks) >= 1

    def test_chunk_has_correct_fields(self):
        text = "# Task\nDo something important and specific here"
        chunks = chunk_prompt(text)
        assert len(chunks) >= 1
        chunk = chunks[0]
        assert isinstance(chunk, PromptChunk)
        assert chunk.content
        assert chunk.index == 0
        assert chunk.token_estimate > 0

    def test_long_text_with_headers(self):
        sections = []
        for i in range(5):
            section = f"## Section {i}\n" + f"Content for section {i}. " * 100
            sections.append(section)
        text = "\n\n".join(sections)
        chunks = chunk_prompt(text)
        assert len(chunks) >= 3  # Some sections may merge


class TestAggregationDimensionScores:
    def test_single_chunk(self):
        analysis = {
            "dimensions": [
                DimensionScore(name="task", score=80, sub_criteria=[]),
                DimensionScore(name="context", score=60, sub_criteria=[]),
                DimensionScore(name="references", score=20, sub_criteria=[]),
                DimensionScore(name="constraints", score=70, sub_criteria=[]),
            ],
            "tcrei_flags": TCREIFlags(task=True, context=True),
        }
        result = aggregate_dimension_scores([analysis], [100])
        # Single chunk should return as-is
        assert result is analysis

    def test_two_chunks_weighted_average(self):
        chunk1 = {
            "dimensions": [
                DimensionScore(name="task", score=80, sub_criteria=[]),
                DimensionScore(name="context", score=60, sub_criteria=[]),
                DimensionScore(name="references", score=20, sub_criteria=[]),
                DimensionScore(name="constraints", score=40, sub_criteria=[]),
            ],
            "tcrei_flags": TCREIFlags(task=True, context=False),
        }
        chunk2 = {
            "dimensions": [
                DimensionScore(name="task", score=40, sub_criteria=[]),
                DimensionScore(name="context", score=80, sub_criteria=[]),
                DimensionScore(name="references", score=60, sub_criteria=[]),
                DimensionScore(name="constraints", score=80, sub_criteria=[]),
            ],
            "tcrei_flags": TCREIFlags(task=False, context=True),
        }
        # Equal weights (100 tokens each)
        result = aggregate_dimension_scores([chunk1, chunk2], [100, 100])
        dims = {d.name: d.score for d in result["dimensions"]}
        assert dims["task"] == 60  # (80 + 40) / 2
        assert dims["context"] == 70  # (60 + 80) / 2

    def test_weighted_by_token_count(self):
        chunk1 = {
            "dimensions": [
                DimensionScore(name="task", score=100, sub_criteria=[]),
                DimensionScore(name="context", score=0, sub_criteria=[]),
                DimensionScore(name="references", score=0, sub_criteria=[]),
                DimensionScore(name="constraints", score=0, sub_criteria=[]),
            ],
            "tcrei_flags": TCREIFlags(),
        }
        chunk2 = {
            "dimensions": [
                DimensionScore(name="task", score=0, sub_criteria=[]),
                DimensionScore(name="context", score=0, sub_criteria=[]),
                DimensionScore(name="references", score=0, sub_criteria=[]),
                DimensionScore(name="constraints", score=0, sub_criteria=[]),
            ],
            "tcrei_flags": TCREIFlags(),
        }
        # chunk1 has 3x the tokens
        result = aggregate_dimension_scores([chunk1, chunk2], [300, 100])
        dims = {d.name: d.score for d in result["dimensions"]}
        assert dims["task"] == 75  # 100 * 0.75 + 0 * 0.25

    def test_or_merge_flags(self):
        chunk1 = {
            "dimensions": [
                DimensionScore(name="task", score=50, sub_criteria=[]),
                DimensionScore(name="context", score=50, sub_criteria=[]),
                DimensionScore(name="references", score=50, sub_criteria=[]),
                DimensionScore(name="constraints", score=50, sub_criteria=[]),
            ],
            "tcrei_flags": TCREIFlags(task=True, context=False, references=False),
        }
        chunk2 = {
            "dimensions": [
                DimensionScore(name="task", score=50, sub_criteria=[]),
                DimensionScore(name="context", score=50, sub_criteria=[]),
                DimensionScore(name="references", score=50, sub_criteria=[]),
                DimensionScore(name="constraints", score=50, sub_criteria=[]),
            ],
            "tcrei_flags": TCREIFlags(task=False, context=True, references=True),
        }
        result = aggregate_dimension_scores([chunk1, chunk2], [100, 100])
        flags = result["tcrei_flags"]
        # OR merge: both should be True
        assert flags.task is True
        assert flags.context is True
        assert flags.references is True

    def test_sub_criteria_deduplication(self):
        chunk1 = {
            "dimensions": [
                DimensionScore(
                    name="task",
                    score=70,
                    sub_criteria=[
                        SubCriterionResult(name="verb", found=True, detail="Found 'write'"),
                    ],
                ),
                DimensionScore(name="context", score=0, sub_criteria=[]),
                DimensionScore(name="references", score=0, sub_criteria=[]),
                DimensionScore(name="constraints", score=0, sub_criteria=[]),
            ],
            "tcrei_flags": TCREIFlags(),
        }
        chunk2 = {
            "dimensions": [
                DimensionScore(
                    name="task",
                    score=50,
                    sub_criteria=[
                        SubCriterionResult(name="verb", found=True, detail="Found action verb 'write' in prompt"),
                    ],
                ),
                DimensionScore(name="context", score=0, sub_criteria=[]),
                DimensionScore(name="references", score=0, sub_criteria=[]),
                DimensionScore(name="constraints", score=0, sub_criteria=[]),
            ],
            "tcrei_flags": TCREIFlags(),
        }
        result = aggregate_dimension_scores([chunk1, chunk2], [100, 100])
        task_dim = next(d for d in result["dimensions"] if d.name == "task")
        # Should be deduplicated — only one "verb" sub-criterion (the longer one)
        verb_scs = [sc for sc in task_dim.sub_criteria if sc.name == "verb"]
        assert len(verb_scs) == 1
        assert "action verb" in verb_scs[0].detail  # the longer detail

    def test_empty_input_returns_empty_analysis(self):
        result = aggregate_dimension_scores([], [])
        assert len(result["dimensions"]) == 4
        for dim in result["dimensions"]:
            assert dim.score == 0
