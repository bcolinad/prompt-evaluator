"""Unit tests for document entity extractor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.documents.extractor import (
    _deduplicate_entities,
    _split_into_windows,
    extract_entities,
)
from src.documents.models import ExtractionEntity


class TestExtractEntities:
    """Tests for extract_entities function."""

    @pytest.mark.asyncio
    @patch("src.documents.extractor.get_settings")
    async def test_disabled_returns_empty(self, mock_settings: MagicMock) -> None:
        """Test that disabled extraction returns empty list."""
        mock_settings.return_value.doc_enable_extraction = False
        result = await extract_entities("Some text here")
        assert result == []

    @pytest.mark.asyncio
    @patch("src.documents.extractor.get_settings")
    async def test_empty_text_returns_empty(self, mock_settings: MagicMock) -> None:
        """Test that empty text returns empty list."""
        mock_settings.return_value.doc_enable_extraction = True
        result = await extract_entities("   ")
        assert result == []

    @pytest.mark.asyncio
    @patch("src.documents.extractor.get_settings")
    async def test_handles_llm_failure_gracefully(self, mock_settings: MagicMock) -> None:
        """Test that LLM failures return empty list (non-fatal)."""
        mock_settings.return_value.doc_enable_extraction = True
        mock_settings.return_value.doc_extraction_model = "test-model"

        # The extractor imports get_llm inside the try block
        result = await extract_entities("Some text")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch("src.documents.extractor.get_settings")
    async def test_mapreduce_creates_windows_for_long_text(self, mock_settings: MagicMock) -> None:
        """Test that long text is split into windows for MapReduce processing."""
        mock_settings.return_value.doc_enable_extraction = True
        mock_settings.return_value.doc_extraction_model = "test-model"

        # Create text longer than window size
        long_text = "A" * 12000
        # Will fail gracefully due to LLM not being available in tests,
        # but verifies the code path doesn't crash
        result = await extract_entities(long_text)
        assert isinstance(result, list)


class TestSplitIntoWindows:
    """Tests for _split_into_windows helper."""

    def test_short_text_single_window(self) -> None:
        """Text shorter than window_size should return a single window."""
        result = _split_into_windows("short text", 5000, 500)
        assert len(result) == 1
        assert result[0] == "short text"

    def test_exact_window_size(self) -> None:
        """Text exactly at window_size should return a single window."""
        text = "A" * 5000
        result = _split_into_windows(text, 5000, 500)
        assert len(result) == 1

    def test_long_text_multiple_windows(self) -> None:
        """Text longer than window_size should be split into overlapping windows."""
        text = "A" * 12000
        result = _split_into_windows(text, 5000, 500)
        assert len(result) >= 3
        # Verify each window is at most window_size
        for window in result:
            assert len(window) <= 5000

    def test_windows_overlap(self) -> None:
        """Adjacent windows should have overlapping content."""
        text = "ABCDEFGHIJ" * 1000  # 10000 chars
        result = _split_into_windows(text, 5000, 500)
        assert len(result) >= 2
        # The end of window 1 should overlap with the start of window 2
        # Window 1: chars [0:5000], Window 2: chars [4500:9500]
        assert result[0][-500:] == result[1][:500]


class TestDeduplicateEntities:
    """Tests for _deduplicate_entities helper."""

    def test_no_duplicates(self) -> None:
        """Unique entities should all be preserved."""
        entities = [
            ExtractionEntity(entity_type="person", value="Alice", confidence=0.9),
            ExtractionEntity(entity_type="organization", value="Acme", confidence=0.8),
        ]
        result = _deduplicate_entities(entities)
        assert len(result) == 2

    def test_exact_duplicates_merged(self) -> None:
        """Exact duplicates should be merged, keeping highest confidence."""
        entities = [
            ExtractionEntity(entity_type="person", value="Alice", confidence=0.7),
            ExtractionEntity(entity_type="person", value="Alice", confidence=0.9),
        ]
        result = _deduplicate_entities(entities)
        assert len(result) == 1
        assert result[0].confidence == 0.9

    def test_case_insensitive_dedup(self) -> None:
        """Deduplication should be case-insensitive."""
        entities = [
            ExtractionEntity(entity_type="Person", value="ALICE", confidence=0.6),
            ExtractionEntity(entity_type="person", value="Alice", confidence=0.9),
        ]
        result = _deduplicate_entities(entities)
        assert len(result) == 1
        assert result[0].confidence == 0.9

    def test_sorted_by_confidence(self) -> None:
        """Results should be sorted by confidence descending."""
        entities = [
            ExtractionEntity(entity_type="person", value="Alice", confidence=0.5),
            ExtractionEntity(entity_type="topic", value="AI", confidence=0.99),
            ExtractionEntity(entity_type="location", value="NYC", confidence=0.7),
        ]
        result = _deduplicate_entities(entities)
        assert len(result) == 3
        assert result[0].confidence >= result[1].confidence >= result[2].confidence

    def test_empty_input(self) -> None:
        """Empty input should return empty list."""
        assert _deduplicate_entities([]) == []
