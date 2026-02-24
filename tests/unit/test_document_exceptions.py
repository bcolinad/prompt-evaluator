"""Unit tests for document processing exceptions."""

from __future__ import annotations

from src.documents.exceptions import DocumentProcessingError, UnsupportedFormatError


class TestDocumentProcessingError:
    """Tests for DocumentProcessingError."""

    def test_basic(self) -> None:
        err = DocumentProcessingError("Something failed")
        assert str(err) == "Something failed"
        assert err.filename is None
        assert err.stage is None

    def test_with_context(self) -> None:
        err = DocumentProcessingError(
            "Load failed",
            filename="test.pdf",
            stage="loader",
        )
        assert err.filename == "test.pdf"
        assert err.stage == "loader"


class TestUnsupportedFormatError:
    """Tests for UnsupportedFormatError."""

    def test_creates_message(self) -> None:
        err = UnsupportedFormatError(".xyz")
        assert ".xyz" in str(err)
        assert err.extension == ".xyz"
        assert err.stage == "loader"

    def test_with_filename(self) -> None:
        err = UnsupportedFormatError(".xyz", filename="test.xyz")
        assert err.filename == "test.xyz"

    def test_is_document_processing_error(self) -> None:
        err = UnsupportedFormatError(".xyz")
        assert isinstance(err, DocumentProcessingError)
