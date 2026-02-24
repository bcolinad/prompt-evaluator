"""Unit tests for document retriever."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.documents.retriever import (
    _build_context,
    _build_where_filters,
    _format_document_header,
    retrieve_document_context,
    retrieve_full_document_text,
)


class TestRetrieveDocumentContext:
    """Tests for retrieve_document_context function."""

    @pytest.mark.asyncio
    @patch("src.documents.retriever.generate_embedding")
    async def test_returns_empty_on_embedding_failure(self, mock_embed: AsyncMock) -> None:
        """Test graceful handling when embedding generation fails."""
        mock_embed.side_effect = RuntimeError("Ollama down")
        session = AsyncMock()
        result = await retrieve_document_context(session, query="test query")
        assert result == ""

    @pytest.mark.asyncio
    @patch("src.documents.retriever.get_settings")
    @patch("src.documents.retriever.generate_embedding")
    async def test_returns_empty_on_zero_chunks(
        self,
        mock_embed: AsyncMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test returns empty string when no chunks exist."""
        mock_embed.return_value = [0.1] * 768
        mock_settings.return_value.doc_max_chunks_per_query = 15

        session = AsyncMock()

        # Count query returns 0
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        session.execute = AsyncMock(return_value=count_result)

        result = await retrieve_document_context(session, query="test")
        assert result == ""

    @pytest.mark.asyncio
    @patch("src.documents.retriever.get_settings")
    @patch("src.documents.retriever.generate_embedding")
    async def test_stuff_strategy_for_small_docs(
        self,
        mock_embed: AsyncMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test that small documents use the stuff strategy (all chunks returned)."""
        mock_embed.return_value = [0.1] * 768
        mock_settings.return_value.doc_max_chunks_per_query = 15

        doc_id = uuid.uuid4()

        # 8 chunks (below _STUFF_THRESHOLD of 50) -> stuff strategy
        chunk_rows = []
        for i in range(8):
            row = MagicMock()
            row.content = f"Chunk {i} content"
            row.page_number = None
            row.section_title = None
            row.chunk_index = i
            row.document_id = doc_id
            chunk_rows.append(row)

        doc_row = MagicMock()
        doc_row.id = doc_id
        doc_row.filename = "small.pdf"
        doc_row.file_type = "pdf"
        doc_row.page_count = 1
        doc_row.word_count = 500
        doc_row.summary = "Small doc."
        doc_row.extractions = None

        session = AsyncMock()

        # Query 1: count -> 8
        count_result = MagicMock()
        count_result.scalar.return_value = 8
        # Query 2: stuff retrieval -> all 8 chunks
        chunks_result = MagicMock()
        chunks_result.fetchall.return_value = chunk_rows
        # Query 3: document metadata
        meta_result = MagicMock()
        meta_result.fetchall.return_value = [doc_row]

        session.execute = AsyncMock(side_effect=[count_result, chunks_result, meta_result])

        result = await retrieve_document_context(session, query="test")
        # All 8 chunks should be present (stuff strategy)
        for i in range(8):
            assert f"Chunk {i} content" in result
        assert "small.pdf" in result
        assert "Complete Document Content" in result  # stuff strategy indicator

    @pytest.mark.asyncio
    @patch("src.documents.retriever.get_settings")
    @patch("src.documents.retriever.generate_embedding")
    async def test_similarity_strategy_for_large_docs(
        self,
        mock_embed: AsyncMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test that large documents use similarity strategy."""
        mock_embed.return_value = [0.1] * 768
        mock_settings.return_value.doc_max_chunks_per_query = 15

        doc_id = uuid.uuid4()

        # top-K chunks (out of 100 total)
        chunk_rows = []
        for i in range(15):
            row = MagicMock()
            row.content = f"Relevant chunk {i}"
            row.page_number = i + 1
            row.section_title = f"Section {i}"
            row.chunk_index = i * 5
            row.document_id = doc_id
            row.distance = 0.1 * i
            chunk_rows.append(row)

        doc_row = MagicMock()
        doc_row.id = doc_id
        doc_row.filename = "large.pdf"
        doc_row.file_type = "pdf"
        doc_row.page_count = 50
        doc_row.word_count = 25000
        doc_row.summary = "Large doc."
        doc_row.extractions = [{"entity_type": "topic", "value": "AI Research"}]

        session = AsyncMock()

        # Query 1: count -> 100 (above _STUFF_THRESHOLD)
        count_result = MagicMock()
        count_result.scalar.return_value = 100
        # Query 2: similarity retrieval -> top 15
        chunks_result = MagicMock()
        chunks_result.fetchall.return_value = chunk_rows
        # Query 3: document metadata
        meta_result = MagicMock()
        meta_result.fetchall.return_value = [doc_row]

        session.execute = AsyncMock(side_effect=[count_result, chunks_result, meta_result])

        result = await retrieve_document_context(session, query="test")
        assert "large.pdf" in result
        assert "AI Research" in result
        assert "Most Relevant Passages" in result  # similarity strategy indicator
        assert "15/100" in result

    @pytest.mark.asyncio
    @patch("src.documents.retriever.get_settings")
    @patch("src.documents.retriever.generate_embedding")
    async def test_returns_formatted_context_with_metadata(
        self,
        mock_embed: AsyncMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test that retrieved chunks include document metadata and entities."""
        mock_embed.return_value = [0.1] * 768
        mock_settings.return_value.doc_max_chunks_per_query = 15

        doc_id = uuid.uuid4()

        row1 = MagicMock()
        row1.content = "First chunk content"
        row1.page_number = 1
        row1.section_title = "Introduction"
        row1.chunk_index = 0
        row1.document_id = doc_id

        doc_row = MagicMock()
        doc_row.id = doc_id
        doc_row.filename = "resume.pdf"
        doc_row.file_type = "pdf"
        doc_row.page_count = 2
        doc_row.word_count = 1288
        doc_row.summary = "A resume."
        doc_row.extractions = [{"entity_type": "person", "value": "Brandon Colina"}]

        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        chunks_result = MagicMock()
        chunks_result.fetchall.return_value = [row1]
        meta_result = MagicMock()
        meta_result.fetchall.return_value = [doc_row]

        session.execute = AsyncMock(side_effect=[count_result, chunks_result, meta_result])

        result = await retrieve_document_context(session, query="test")
        assert "First chunk content" in result
        assert "Introduction" in result
        assert "resume.pdf" in result
        assert "Brandon Colina" in result

    @pytest.mark.asyncio
    @patch("src.documents.retriever.get_settings")
    @patch("src.documents.retriever.generate_embedding")
    async def test_handles_query_failure(
        self,
        mock_embed: AsyncMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test graceful handling of database query failures."""
        mock_embed.return_value = [0.1] * 768
        mock_settings.return_value.doc_max_chunks_per_query = 15

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=RuntimeError("DB error"))

        result = await retrieve_document_context(session, query="test")
        assert result == ""


class TestRetrieveFullDocumentText:
    """Tests for retrieve_full_document_text function."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_invalid_ids(self) -> None:
        """Test that invalid UUIDs return empty string."""
        session = AsyncMock()
        result = await retrieve_full_document_text(session, ["not-a-uuid"])
        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_ids(self) -> None:
        """Test that empty list returns empty string."""
        session = AsyncMock()
        result = await retrieve_full_document_text(session, [])
        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_full_text_with_metadata(self) -> None:
        """Test that full document text includes metadata and content."""
        doc_id = uuid.uuid4()
        row = MagicMock()
        row.id = doc_id
        row.filename = "report.pdf"
        row.file_type = "pdf"
        row.page_count = 10
        row.word_count = 5000
        row.raw_text = "Full document content here with all details."
        row.extractions = [{"entity_type": "topic", "value": "Machine Learning"}]

        session = AsyncMock()
        query_result = MagicMock()
        query_result.fetchall.return_value = [row]
        session.execute = AsyncMock(return_value=query_result)

        result = await retrieve_full_document_text(session, [str(doc_id)])
        assert "report.pdf" in result
        assert "Full document content here with all details." in result
        assert "Machine Learning" in result
        assert "Full document content:" in result

    @pytest.mark.asyncio
    async def test_handles_db_failure(self) -> None:
        """Test graceful handling of database failures."""
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=RuntimeError("DB error"))

        doc_id = uuid.uuid4()
        result = await retrieve_full_document_text(session, [str(doc_id)])
        assert result == ""


class TestBuildWhereFilters:
    """Tests for _build_where_filters helper."""

    def test_all_none(self) -> None:
        filters = _build_where_filters(None, None, None)
        assert filters["user_id"] is None
        assert filters["thread_id"] is None
        assert filters["parsed_uuids"] == []

    def test_anonymous_user_ignored(self) -> None:
        filters = _build_where_filters("anonymous", None, None)
        assert filters["user_id"] is None

    def test_valid_user_and_thread(self) -> None:
        filters = _build_where_filters("user1", "thread1", None)
        assert filters["user_id"] == "user1"
        assert filters["thread_id"] == "thread1"

    def test_document_ids_parsed(self) -> None:
        doc_id = str(uuid.uuid4())
        filters = _build_where_filters(None, None, [doc_id, "invalid"])
        assert len(filters["parsed_uuids"]) == 1


class TestBuildContext:
    """Tests for _build_context helper."""

    def test_stuff_strategy_label(self) -> None:
        row = MagicMock()
        row.content = "Some content"
        row.section_title = None
        row.page_number = None
        row.document_id = uuid.uuid4()

        result = _build_context([row], {}, "stuff", 5)
        assert "Complete Document Content" in result
        assert "5" in result

    def test_similarity_strategy_label(self) -> None:
        row = MagicMock()
        row.content = "Relevant content"
        row.section_title = "Intro"
        row.page_number = 1
        row.document_id = uuid.uuid4()

        result = _build_context([row], {}, "similarity", 100)
        assert "Most Relevant Passages" in result
        assert "1/100" in result


class TestFormatDocumentHeader:
    """Tests for the document header formatter."""

    def test_basic_header(self) -> None:
        meta = {
            "filename": "report.pdf",
            "file_type": "pdf",
            "page_count": 10,
            "word_count": 5000,
            "summary": None,
            "extractions": None,
        }
        header = _format_document_header(meta)
        assert "report.pdf" in header
        assert "PDF" in header
        assert "5,000" in header

    def test_header_with_entities(self) -> None:
        meta = {
            "filename": "resume.pdf",
            "file_type": "pdf",
            "page_count": 1,
            "word_count": 1000,
            "summary": None,
            "extractions": [
                {"entity_type": "person", "value": "Jane Doe"},
                {"entity_type": "organization", "value": "Acme Corp"},
            ],
        }
        header = _format_document_header(meta)
        assert "Jane Doe" in header
        assert "Acme Corp" in header
        assert "Key entities" in header

    def test_header_no_optional_fields(self) -> None:
        meta = {
            "filename": "data.csv",
            "file_type": "csv",
            "page_count": None,
            "word_count": None,
            "summary": None,
            "extractions": None,
        }
        header = _format_document_header(meta)
        assert "data.csv" in header
        assert "CSV" in header
