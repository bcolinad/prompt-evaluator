"""Unit tests for document processor orchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from src.documents.exceptions import DocumentProcessingError
from src.documents.models import DocumentChunk, DocumentMetadata
from src.documents.processor import _generate_summary, is_supported_document, process_document


class TestIsSupported:
    """Tests for is_supported_document function."""

    def test_pdf_supported(self) -> None:
        assert is_supported_document("report.pdf") is True

    def test_docx_supported(self) -> None:
        assert is_supported_document("doc.docx") is True

    def test_xlsx_supported(self) -> None:
        assert is_supported_document("sheet.xlsx") is True

    def test_pptx_supported(self) -> None:
        assert is_supported_document("slides.pptx") is True

    def test_csv_supported(self) -> None:
        assert is_supported_document("data.csv") is True

    def test_txt_not_supported(self) -> None:
        assert is_supported_document("readme.txt") is False

    def test_py_not_supported(self) -> None:
        assert is_supported_document("script.py") is False

    def test_case_insensitive(self) -> None:
        assert is_supported_document("REPORT.PDF") is True


class TestGenerateSummary:
    """Tests for _generate_summary helper."""

    def test_short_text(self) -> None:
        summary = _generate_summary("Hello world", "test.pdf")
        assert "test.pdf" in summary
        assert "Hello world" in summary

    def test_long_text_has_preview_and_stats(self) -> None:
        text = "A" * 5000
        summary = _generate_summary(text, "big.pdf")
        assert "big.pdf" in summary
        assert "5,000 characters" in summary
        assert "more characters" in summary  # truncation indicator


class TestProcessDocument:
    """Tests for process_document orchestrator."""

    @pytest.mark.asyncio
    async def test_file_too_large(self, tmp_path: Path) -> None:
        """Test that oversized files are rejected."""
        large_file = tmp_path / "huge.pdf"
        large_file.write_bytes(b"x" * 1024)

        mock_session = AsyncMock()

        with patch("src.documents.processor.get_settings") as mock_settings:
            mock_settings.return_value.doc_max_file_size = 100  # 100 bytes
            mock_settings.return_value.doc_chunk_size = 1000
            mock_settings.return_value.doc_chunk_overlap = 200
            mock_settings.return_value.doc_enable_extraction = False
            with pytest.raises(DocumentProcessingError, match="exceeds"):
                await process_document(mock_session, large_file)

    @pytest.mark.asyncio
    async def test_missing_file(self, tmp_path: Path) -> None:
        """Test that missing files raise an error."""
        missing = tmp_path / "nonexistent.pdf"
        mock_session = AsyncMock()

        with pytest.raises(DocumentProcessingError, match="Cannot access"):
            await process_document(mock_session, missing)

    @pytest.mark.asyncio
    @patch("src.documents.processor.vectorize_and_store")
    @patch("src.documents.processor.extract_entities")
    @patch("src.documents.processor.chunk_document")
    @patch("src.documents.processor.load_document")
    @patch("src.documents.processor.get_settings")
    async def test_full_pipeline(
        self,
        mock_settings: MagicMock,
        mock_load: AsyncMock,
        mock_chunk: MagicMock,
        mock_extract: AsyncMock,
        mock_vectorize: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test the full processing pipeline runs all stages."""
        # Setup
        test_file = tmp_path / "test.csv"
        test_file.write_text("name,age\nAlice,30")

        mock_settings.return_value.doc_max_file_size = 100 * 1024 * 1024
        mock_settings.return_value.doc_chunk_size = 1000
        mock_settings.return_value.doc_chunk_overlap = 200
        mock_settings.return_value.doc_enable_extraction = True

        mock_load.return_value = (
            "name | age\nAlice | 30",
            DocumentMetadata(
                filename="test.csv",
                file_type="csv",
                file_size_bytes=20,
                word_count=4,
            ),
        )
        mock_chunk.return_value = [
            DocumentChunk(chunk_index=0, content="name | age\nAlice | 30", token_estimate=5),
        ]
        mock_extract.return_value = []
        mock_vectorize.return_value = []

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        result = await process_document(
            mock_session,
            test_file,
            filename="test.csv",
            user_id="user1",
            thread_id="thread1",
        )

        assert result.filename == "test.csv"
        assert result.chunk_count == 1
        assert result.processing_time_seconds > 0
        mock_load.assert_called_once()
        mock_chunk.assert_called_once()
        mock_extract.assert_called_once()
        mock_vectorize.assert_called_once()
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.documents.processor.load_document")
    @patch("src.documents.processor.get_settings")
    async def test_empty_document_raises(
        self,
        mock_settings: MagicMock,
        mock_load: AsyncMock,
        tmp_path: Path,
    ) -> None:
        """Test that empty documents raise an error."""
        test_file = tmp_path / "empty.csv"
        test_file.write_text("")

        mock_settings.return_value.doc_max_file_size = 100 * 1024 * 1024

        mock_load.return_value = (
            "   ",
            DocumentMetadata(filename="empty.csv", file_type="csv", file_size_bytes=0),
        )

        mock_session = AsyncMock()

        with pytest.raises(DocumentProcessingError, match="empty"):
            await process_document(mock_session, test_file)
