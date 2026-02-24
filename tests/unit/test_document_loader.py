"""Unit tests for document loader."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from src.documents.exceptions import DocumentProcessingError, UnsupportedFormatError
from src.documents.loader import (
    SUPPORTED_EXTENSIONS,
    _count_words,
    _pdfplumber_available,
    _pymupdf_available,
    load_document,
)


class TestSupportedExtensions:
    """Tests for supported extension constants."""

    def test_includes_core_formats(self) -> None:
        for ext in [".pdf", ".docx", ".xlsx", ".pptx", ".csv"]:
            assert ext in SUPPORTED_EXTENSIONS

    def test_does_not_include_text_files(self) -> None:
        assert ".txt" not in SUPPORTED_EXTENSIONS
        assert ".py" not in SUPPORTED_EXTENSIONS


class TestCountWords:
    """Tests for _count_words helper."""

    def test_empty_string(self) -> None:
        assert _count_words("") == 0

    def test_simple_text(self) -> None:
        assert _count_words("hello world") == 2

    def test_multiline(self) -> None:
        assert _count_words("one\ntwo\nthree") == 3


class TestLoadDocument:
    """Tests for load_document function."""

    @pytest.mark.asyncio
    async def test_unsupported_extension(self, tmp_path: Path) -> None:
        file = tmp_path / "test.xyz"
        file.write_text("content")
        with pytest.raises(UnsupportedFormatError):
            await load_document(file)

    @pytest.mark.asyncio
    async def test_missing_file(self, tmp_path: Path) -> None:
        file = tmp_path / "nonexistent.pdf"
        with pytest.raises(DocumentProcessingError):
            await load_document(file)

    @pytest.mark.asyncio
    async def test_csv_loading(self, tmp_path: Path) -> None:
        """Test CSV files can be loaded."""
        csv_file = tmp_path / "data.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Age", "City"])
            writer.writerow(["Alice", "30", "NYC"])
            writer.writerow(["Bob", "25", "LA"])
        text, metadata = await load_document(csv_file)
        assert "Alice" in text
        assert "Bob" in text
        assert metadata.file_type == "csv"
        assert metadata.word_count is not None
        assert metadata.word_count > 0

    @pytest.mark.asyncio
    async def test_explicit_filename(self, tmp_path: Path) -> None:
        """Test that explicit filename overrides path-based detection."""
        csv_file = tmp_path / "data.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["test"])
        _text, metadata = await load_document(csv_file, filename="custom_name.csv")
        assert metadata.filename == "custom_name.csv"

    @pytest.mark.asyncio
    @patch("src.documents.loader._load_pdf")
    async def test_pdf_delegates_to_loader(self, mock_load_pdf: AsyncMock, tmp_path: Path) -> None:
        """Test PDF loading delegates to the correct loader."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake pdf content")
        mock_load_pdf.return_value = ("Extracted text from PDF", 5, {"pdf_extraction_method": "pypdf"})
        text, metadata = await load_document(pdf_file)
        assert text == "Extracted text from PDF"
        assert metadata.page_count == 5
        assert metadata.file_type == "pdf"
        assert metadata.extra["pdf_extraction_method"] == "pypdf"

    @pytest.mark.asyncio
    @patch("src.documents.loader._load_docx")
    async def test_docx_delegates_to_loader(self, mock_load_docx: AsyncMock, tmp_path: Path) -> None:
        """Test DOCX loading delegates to the correct loader."""
        docx_file = tmp_path / "test.docx"
        docx_file.write_bytes(b"fake docx content")
        mock_load_docx.return_value = ("Extracted text from DOCX", None)
        text, metadata = await load_document(docx_file)
        assert text == "Extracted text from DOCX"
        assert metadata.file_type == "docx"


class TestPdfOcrFallback:
    """Tests for tiered PDF OCR fallback in _load_pdf."""

    def _make_settings(self, *, ocr_enabled: bool = True, min_chars: int = 50) -> MagicMock:
        """Create a mock Settings instance for OCR tests."""
        settings = MagicMock()
        settings.pdf_ocr_enabled = ocr_enabled
        settings.pdf_ocr_min_text_chars = min_chars
        return settings

    @pytest.mark.asyncio
    @patch("src.documents.loader.get_settings")
    @patch("src.documents.loader._pdfplumber_available", return_value=False)
    @patch("src.documents.loader._pymupdf_available", return_value=False)
    async def test_tier1_sufficient_no_fallback(
        self,
        _mock_pymupdf: MagicMock,
        _mock_pdfplumber: MagicMock,
        mock_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When Tier 1 extracts enough text, no fallback is attempted."""
        mock_settings.return_value = self._make_settings(min_chars=10)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        mock_page = MagicMock()
        mock_page.page_content = "This is a long enough text from the PDF document."

        with patch("langchain_community.document_loaders.PyPDFLoader") as mock_loader_cls:
            mock_loader = MagicMock()
            mock_loader.aload = AsyncMock(return_value=[mock_page])
            mock_loader_cls.return_value = mock_loader

            from src.documents.loader import _load_pdf

            text, page_count, extra = await _load_pdf(pdf_file)

        assert "long enough text" in text
        assert page_count == 1
        assert extra["pdf_extraction_method"] == "pypdf"
        assert extra["pdf_ocr_applied"] == "false"
        assert extra["pdf_tiers_attempted"] == "pypdf"

    @pytest.mark.asyncio
    @patch("src.documents.loader.get_settings")
    @patch("src.documents.loader._pdfplumber_available", return_value=True)
    @patch("src.documents.loader._pymupdf_available", return_value=False)
    async def test_tier2_triggered_on_low_text(
        self,
        _mock_pymupdf: MagicMock,
        _mock_pdfplumber: MagicMock,
        mock_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When Tier 1 produces too little text, pdfplumber is attempted."""
        mock_settings.return_value = self._make_settings(min_chars=50)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        mock_page = MagicMock()
        mock_page.page_content = "Short"

        pdfplumber_text = "This is a much longer text extracted by pdfplumber from the scanned PDF document."

        with (
            patch("langchain_community.document_loaders.PyPDFLoader") as mock_loader_cls,
            patch(
                "src.documents.loader._extract_with_pdfplumber_sync",
                return_value=pdfplumber_text,
            ) as mock_extract,
            patch("asyncio.to_thread", side_effect=lambda fn, *a: fn(*a)) as _mock_thread,
        ):
            mock_loader = MagicMock()
            mock_loader.aload = AsyncMock(return_value=[mock_page])
            mock_loader_cls.return_value = mock_loader

            from src.documents.loader import _load_pdf

            text, _page_count, extra = await _load_pdf(pdf_file)

        mock_extract.assert_called_once_with(pdf_file)
        assert "pdfplumber" in text
        assert extra["pdf_extraction_method"] == "pdfplumber"
        assert "pdfplumber" in extra["pdf_tiers_attempted"]

    @pytest.mark.asyncio
    @patch("src.documents.loader.get_settings")
    @patch("src.documents.loader._pdfplumber_available", return_value=True)
    @patch("src.documents.loader._pymupdf_available", return_value=True)
    async def test_tier3_triggered_when_tier2_insufficient(
        self,
        _mock_pymupdf: MagicMock,
        _mock_pdfplumber: MagicMock,
        mock_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When both Tier 1 and Tier 2 produce too little text, PyMuPDF OCR is attempted."""
        mock_settings.return_value = self._make_settings(min_chars=100)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        mock_page = MagicMock()
        mock_page.page_content = "Short"

        ocr_text = "A" * 150  # plenty of OCR text

        with (
            patch("langchain_community.document_loaders.PyPDFLoader") as mock_loader_cls,
            patch("src.documents.loader._extract_with_pdfplumber_sync", return_value="tiny"),
            patch(
                "src.documents.loader._extract_with_pymupdf_ocr_sync",
                return_value=ocr_text,
            ) as mock_ocr,
            patch("asyncio.to_thread", side_effect=lambda fn, *a: fn(*a)),
        ):
            mock_loader = MagicMock()
            mock_loader.aload = AsyncMock(return_value=[mock_page])
            mock_loader_cls.return_value = mock_loader

            from src.documents.loader import _load_pdf

            text, _page_count, extra = await _load_pdf(pdf_file)

        mock_ocr.assert_called_once_with(pdf_file)
        assert text == ocr_text
        assert extra["pdf_extraction_method"] == "pymupdf_ocr"
        assert extra["pdf_ocr_applied"] == "true"
        assert "pymupdf_ocr" in extra["pdf_tiers_attempted"]

    @pytest.mark.asyncio
    @patch("src.documents.loader.get_settings")
    @patch("src.documents.loader._pdfplumber_available", return_value=False)
    @patch("src.documents.loader._pymupdf_available", return_value=False)
    async def test_graceful_when_optional_deps_missing(
        self,
        _mock_pymupdf: MagicMock,
        _mock_pdfplumber: MagicMock,
        mock_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When optional deps are missing, returns Tier 1 result even if sparse."""
        mock_settings.return_value = self._make_settings(min_chars=1000)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        mock_page = MagicMock()
        mock_page.page_content = "Short text"

        with patch("langchain_community.document_loaders.PyPDFLoader") as mock_loader_cls:
            mock_loader = MagicMock()
            mock_loader.aload = AsyncMock(return_value=[mock_page])
            mock_loader_cls.return_value = mock_loader

            from src.documents.loader import _load_pdf

            text, _page_count, extra = await _load_pdf(pdf_file)

        assert text == "Short text"
        assert extra["pdf_extraction_method"] == "pypdf"
        assert extra["pdf_tiers_attempted"] == "pypdf"

    @pytest.mark.asyncio
    @patch("src.documents.loader.get_settings")
    @patch("src.documents.loader._pdfplumber_available", return_value=True)
    @patch("src.documents.loader._pymupdf_available", return_value=True)
    async def test_all_fallbacks_fail_returns_best(
        self,
        _mock_pymupdf: MagicMock,
        _mock_pdfplumber: MagicMock,
        mock_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When all fallback tiers raise exceptions, returns the best text found."""
        mock_settings.return_value = self._make_settings(min_chars=1000)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        mock_page = MagicMock()
        mock_page.page_content = "Some pypdf text"

        with (
            patch("langchain_community.document_loaders.PyPDFLoader") as mock_loader_cls,
            patch("src.documents.loader._extract_with_pdfplumber_sync", side_effect=RuntimeError("pdfplumber boom")),
            patch(
                "src.documents.loader._extract_with_pymupdf_ocr_sync", side_effect=RuntimeError("pymupdf boom")
            ),
            patch("asyncio.to_thread", side_effect=lambda fn, *a: fn(*a)),
        ):
            mock_loader = MagicMock()
            mock_loader.aload = AsyncMock(return_value=[mock_page])
            mock_loader_cls.return_value = mock_loader

            from src.documents.loader import _load_pdf

            text, _page_count, extra = await _load_pdf(pdf_file)

        assert text == "Some pypdf text"
        assert extra["pdf_extraction_method"] == "pypdf"
        assert "pdfplumber" in extra["pdf_tiers_attempted"]
        assert "pymupdf_ocr" in extra["pdf_tiers_attempted"]

    @pytest.mark.asyncio
    @patch("src.documents.loader.get_settings")
    @patch("src.documents.loader._pdfplumber_available", return_value=True)
    @patch("src.documents.loader._pymupdf_available", return_value=True)
    async def test_ocr_disabled_skips_fallback(
        self,
        _mock_pymupdf: MagicMock,
        _mock_pdfplumber: MagicMock,
        mock_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When OCR is disabled via settings, only Tier 1 runs."""
        mock_settings.return_value = self._make_settings(ocr_enabled=False, min_chars=1000)
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake")

        mock_page = MagicMock()
        mock_page.page_content = "Short"

        with patch("langchain_community.document_loaders.PyPDFLoader") as mock_loader_cls:
            mock_loader = MagicMock()
            mock_loader.aload = AsyncMock(return_value=[mock_page])
            mock_loader_cls.return_value = mock_loader

            from src.documents.loader import _load_pdf

            text, _page_count, extra = await _load_pdf(pdf_file)

        assert text == "Short"
        assert extra["pdf_extraction_method"] == "pypdf"
        assert extra["pdf_ocr_applied"] == "false"
        assert extra["pdf_tiers_attempted"] == "pypdf"

    @pytest.mark.asyncio
    @patch("src.documents.loader._load_pdf")
    async def test_extra_metadata_propagated_to_document_metadata(
        self, mock_load_pdf: AsyncMock, tmp_path: Path
    ) -> None:
        """Extra metadata from _load_pdf is propagated into DocumentMetadata.extra."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake pdf")
        mock_load_pdf.return_value = (
            "OCR extracted text from a scanned document",
            3,
            {
                "pdf_extraction_method": "pymupdf_ocr",
                "pdf_ocr_applied": "true",
                "pdf_tiers_attempted": "pypdf,pdfplumber,pymupdf_ocr",
            },
        )
        _text, metadata = await load_document(pdf_file)
        assert metadata.extra["pdf_extraction_method"] == "pymupdf_ocr"
        assert metadata.extra["pdf_ocr_applied"] == "true"
        assert "pymupdf_ocr" in metadata.extra["pdf_tiers_attempted"]


class TestOcrAvailabilityProbes:
    """Tests for the optional dependency probe functions."""

    @patch.dict("sys.modules", {"pdfplumber": MagicMock()})
    def test_pdfplumber_available_when_installed(self) -> None:
        assert _pdfplumber_available() is True

    @patch.dict("sys.modules", {"pdfplumber": None})
    def test_pdfplumber_not_available_when_missing(self) -> None:
        assert _pdfplumber_available() is False

    @patch.dict("sys.modules", {"fitz": MagicMock()})
    def test_pymupdf_available_when_installed(self) -> None:
        assert _pymupdf_available() is True

    @patch.dict("sys.modules", {"fitz": None})
    def test_pymupdf_not_available_when_missing(self) -> None:
        assert _pymupdf_available() is False
