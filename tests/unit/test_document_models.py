"""Unit tests for document processing Pydantic models."""

from __future__ import annotations

import uuid

from src.documents.models import DocumentChunk, DocumentMetadata, ExtractionEntity, ProcessingResult


class TestDocumentMetadata:
    """Tests for DocumentMetadata model."""

    def test_basic_creation(self) -> None:
        meta = DocumentMetadata(
            filename="report.pdf",
            file_type="pdf",
            file_size_bytes=1024,
        )
        assert meta.filename == "report.pdf"
        assert meta.file_type == "pdf"
        assert meta.file_size_bytes == 1024
        assert meta.page_count is None
        assert meta.word_count is None

    def test_full_creation(self) -> None:
        meta = DocumentMetadata(
            filename="doc.docx",
            file_type="docx",
            file_size_bytes=2048,
            page_count=10,
            word_count=5000,
            title="Test Document",
            author="Test Author",
            extra={"language": "en"},
        )
        assert meta.page_count == 10
        assert meta.word_count == 5000
        assert meta.title == "Test Document"
        assert meta.extra == {"language": "en"}


class TestDocumentChunk:
    """Tests for DocumentChunk model."""

    def test_basic_creation(self) -> None:
        chunk = DocumentChunk(
            chunk_index=0,
            content="This is chunk content.",
        )
        assert chunk.chunk_index == 0
        assert chunk.content == "This is chunk content."
        assert chunk.page_number is None
        assert chunk.token_estimate == 0

    def test_full_creation(self) -> None:
        chunk = DocumentChunk(
            chunk_index=3,
            content="Slide content here",
            page_number=4,
            section_title="Introduction",
            char_offset=1500,
            token_estimate=250,
        )
        assert chunk.page_number == 4
        assert chunk.section_title == "Introduction"
        assert chunk.char_offset == 1500
        assert chunk.token_estimate == 250


class TestExtractionEntity:
    """Tests for ExtractionEntity model."""

    def test_basic_creation(self) -> None:
        entity = ExtractionEntity(
            entity_type="person",
            value="John Doe",
        )
        assert entity.entity_type == "person"
        assert entity.value == "John Doe"
        assert entity.confidence == 1.0

    def test_with_confidence(self) -> None:
        entity = ExtractionEntity(
            entity_type="organization",
            value="Acme Corp",
            confidence=0.85,
            metadata={"source": "page1"},
        )
        assert entity.confidence == 0.85
        assert entity.metadata == {"source": "page1"}


class TestProcessingResult:
    """Tests for ProcessingResult model."""

    def test_basic_creation(self) -> None:
        result = ProcessingResult(
            filename="test.pdf",
            file_type="pdf",
            file_size_bytes=1024,
            raw_text="Hello world",
            summary="Document summary",
            chunk_count=5,
        )
        assert result.filename == "test.pdf"
        assert result.chunk_count == 5
        assert isinstance(result.document_id, uuid.UUID)

    def test_display_summary_minimal(self) -> None:
        result = ProcessingResult(
            filename="test.csv",
            file_type="csv",
            file_size_bytes=100,
            raw_text="data",
            summary="Test",
            chunk_count=1,
        )
        display = result.display_summary
        assert "test.csv" in display
        assert "1 chunks stored" in display

    def test_display_summary_full(self) -> None:
        result = ProcessingResult(
            filename="report.pdf",
            file_type="pdf",
            file_size_bytes=50000,
            page_count=45,
            word_count=12500,
            raw_text="text content",
            summary="Summary",
            chunk_count=48,
        )
        display = result.display_summary
        assert "report.pdf" in display
        assert "45 pages" in display
        assert "12,500 words" in display
        assert "48 chunks stored" in display
