"""Unit tests for document vectorizer."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.documents.models import DocumentChunk
from src.documents.vectorizer import vectorize_and_store


class TestVectorizeAndStore:
    """Tests for vectorize_and_store function."""

    @pytest.mark.asyncio
    @patch("src.documents.vectorizer.generate_embedding")
    async def test_vectorizes_all_chunks(self, mock_embed: AsyncMock) -> None:
        """Test that all chunks get embeddings and are stored."""
        mock_embed.return_value = [0.1] * 768

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        doc_id = uuid.uuid4()
        chunks = [
            DocumentChunk(chunk_index=0, content="First chunk", token_estimate=3),
            DocumentChunk(chunk_index=1, content="Second chunk", token_estimate=3),
        ]

        records = await vectorize_and_store(session, doc_id, chunks, user_id="user1")

        assert len(records) == 2
        assert session.add.call_count == 2
        assert mock_embed.call_count == 2

    @pytest.mark.asyncio
    @patch("src.documents.vectorizer.generate_embedding")
    async def test_skips_failed_embeddings(self, mock_embed: AsyncMock) -> None:
        """Test that individual embedding failures don't stop processing."""
        # First succeeds, second fails
        mock_embed.side_effect = [[0.1] * 768, RuntimeError("Embed failed")]

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        doc_id = uuid.uuid4()
        chunks = [
            DocumentChunk(chunk_index=0, content="Good chunk", token_estimate=3),
            DocumentChunk(chunk_index=1, content="Bad chunk", token_estimate=3),
        ]

        records = await vectorize_and_store(session, doc_id, chunks)

        assert len(records) == 1
        assert session.add.call_count == 1

    @pytest.mark.asyncio
    @patch("src.documents.vectorizer.generate_embedding")
    async def test_empty_chunks(self, mock_embed: AsyncMock) -> None:
        """Test with empty chunk list."""
        session = AsyncMock()
        session.flush = AsyncMock()

        records = await vectorize_and_store(session, uuid.uuid4(), [])

        assert len(records) == 0
        mock_embed.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.documents.vectorizer.generate_embedding")
    async def test_passes_user_and_thread(self, mock_embed: AsyncMock) -> None:
        """Test that user_id and thread_id are passed to records."""
        mock_embed.return_value = [0.1] * 768

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        doc_id = uuid.uuid4()
        chunks = [DocumentChunk(chunk_index=0, content="Test", token_estimate=1)]

        records = await vectorize_and_store(
            session,
            doc_id,
            chunks,
            user_id="user1",
            thread_id="thread1",
        )

        assert len(records) == 1
        assert records[0].user_id == "user1"
        assert records[0].thread_id == "thread1"
