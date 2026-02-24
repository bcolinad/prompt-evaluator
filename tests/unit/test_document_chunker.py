"""Unit tests for document chunker."""

from __future__ import annotations

from unittest.mock import patch

from src.documents.chunker import _estimate_page_number, _extract_section_title, chunk_document


class TestChunkDocument:
    """Tests for chunk_document function."""

    def test_short_text_single_chunk(self) -> None:
        text = "This is a short document."
        chunks = chunk_document(text, chunk_size=1000, chunk_overlap=100)
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert chunks[0].content == text
        assert chunks[0].token_estimate == len(text) // 4

    def test_long_text_multiple_chunks(self) -> None:
        text = "Word " * 500  # 2500 characters
        chunks = chunk_document(text, chunk_size=500, chunk_overlap=50)
        assert len(chunks) > 1
        # All chunks have sequential indexes
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_empty_text(self) -> None:
        chunks = chunk_document("", chunk_size=1000, chunk_overlap=100)
        # Empty text should still return at least an empty chunk or nothing
        assert len(chunks) <= 1

    def test_chunk_has_offset(self) -> None:
        text = "First section.\n\nSecond section with more text here.\n\nThird section."
        chunks = chunk_document(text, chunk_size=30, chunk_overlap=5)
        # First chunk should have offset 0
        if chunks:
            assert chunks[0].char_offset == 0

    @patch("src.documents.chunker.get_settings")
    def test_uses_settings_defaults(self, mock_settings) -> None:
        mock_settings.return_value.doc_chunk_size = 500
        mock_settings.return_value.doc_chunk_overlap = 100
        text = "Test content " * 100
        chunks = chunk_document(text)
        assert len(chunks) >= 1


class TestEstimatePageNumber:
    """Tests for _estimate_page_number helper."""

    def test_with_form_feed(self) -> None:
        text = "Page 1\fPage 2\fPage 3"
        # Offset in page 3
        assert _estimate_page_number(text, len("Page 1\fPage 2\f")) == 3

    def test_with_slide_markers(self) -> None:
        text = "## Slide 1\nContent\n## Slide 2\nContent\n## Slide 3\n"
        offset = len("## Slide 1\nContent\n## Slide 2\nContent\n")
        result = _estimate_page_number(text, offset)
        assert result == 2

    def test_no_markers(self) -> None:
        text = "Just plain text without any markers."
        assert _estimate_page_number(text, 10) is None


class TestExtractSectionTitle:
    """Tests for _extract_section_title helper."""

    def test_with_heading(self) -> None:
        text = "## Introduction\nThis is the intro."
        assert _extract_section_title(text) == "Introduction"

    def test_with_h3(self) -> None:
        text = "### Details\nSome details."
        assert _extract_section_title(text) == "Details"

    def test_no_heading(self) -> None:
        text = "Just regular text without headings."
        assert _extract_section_title(text) is None

    def test_heading_truncated(self) -> None:
        long_title = "A" * 600
        text = f"## {long_title}\nContent"
        result = _extract_section_title(text)
        assert result is not None
        assert len(result) <= 512
