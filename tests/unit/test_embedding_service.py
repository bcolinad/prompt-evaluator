"""Unit tests for the embedding service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.embeddings.service import (
    _build_summary_text,
    find_similar_evaluations,
    generate_embedding,
    store_evaluation_embedding,
)


class TestBuildSummaryText:
    def test_basic_summary(self):
        result = _build_summary_text(
            input_text="Write about dogs",
            rewritten_prompt=None,
            overall_score=45,
            grade="Needs Work",
            output_score=None,
            improvements_summary=None,
        )
        assert "Prompt: Write about dogs" in result
        assert "Score: 45/100 (Needs Work)" in result

    def test_full_summary(self):
        result = _build_summary_text(
            input_text="Write about dogs",
            rewritten_prompt="As a vet, write a detailed blog post...",
            overall_score=85,
            grade="Excellent",
            output_score=0.92,
            improvements_summary="Add persona; Add constraints",
        )
        assert "Score: 85/100 (Excellent)" in result
        assert "Output quality: 92%" in result
        assert "Improvements: Add persona" in result
        assert "Rewritten: As a vet" in result

    def test_truncates_long_rewrite(self):
        long_rewrite = "x" * 600
        result = _build_summary_text(
            input_text="test",
            rewritten_prompt=long_rewrite,
            overall_score=50,
            grade="Needs Work",
            output_score=None,
            improvements_summary=None,
        )
        # Should truncate to 500 chars
        assert len(result.split("Rewritten: ")[1]) == 500


class TestGenerateEmbedding:
    @pytest.mark.asyncio
    async def test_calls_embeddings_model(self):
        mock_embedding = [0.1] * 768
        with patch("src.embeddings.service._get_embeddings_model") as mock_model:
            mock_instance = MagicMock()
            mock_instance.aembed_query = AsyncMock(return_value=mock_embedding)
            mock_model.return_value = mock_instance

            result = await generate_embedding("test text")

            mock_instance.aembed_query.assert_called_once_with("test text")
            assert result == mock_embedding
            assert len(result) == 768


class TestStoreEvaluationEmbedding:
    @pytest.mark.asyncio
    async def test_stores_embedding_record(self):
        mock_embedding = [0.1] * 768
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        with patch("src.embeddings.service.generate_embedding", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_embedding

            result = await store_evaluation_embedding(
                session=mock_session,
                user_id=None,
                evaluation_id=None,
                input_text="Write about dogs",
                rewritten_prompt="As a vet...",
                overall_score=65,
                grade="Good",
                output_score=0.75,
                improvements_summary="Add persona",
            )

            mock_gen.assert_called_once()
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()
            assert result.input_text == "Write about dogs"
            assert result.overall_score == 65
            assert result.grade == "Good"

    @pytest.mark.asyncio
    async def test_stores_with_thread_id(self):
        mock_embedding = [0.1] * 768
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        with patch("src.embeddings.service.generate_embedding", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_embedding

            result = await store_evaluation_embedding(
                session=mock_session,
                user_id="user-1",
                evaluation_id=None,
                input_text="Test prompt",
                rewritten_prompt=None,
                overall_score=70,
                grade="Good",
                output_score=None,
                improvements_summary=None,
                thread_id="thread-abc-123",
            )

            assert result.thread_id == "thread-abc-123"
            mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_stores_with_anonymous_user(self):
        mock_embedding = [0.1] * 768
        mock_session = AsyncMock()
        mock_session.add = MagicMock()

        with patch("src.embeddings.service.generate_embedding", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_embedding

            result = await store_evaluation_embedding(
                session=mock_session,
                user_id="anonymous",
                evaluation_id=None,
                input_text="test",
                rewritten_prompt=None,
                overall_score=30,
                grade="Weak",
                output_score=None,
                improvements_summary=None,
            )

            assert result.user_id is None


class TestFindSimilarEvaluations:
    @pytest.mark.asyncio
    async def test_returns_similar_evaluations(self):
        mock_embedding = [0.1] * 768
        mock_row = MagicMock()
        mock_row.input_text = "Write about cats"
        mock_row.rewritten_prompt = "As a vet..."
        mock_row.overall_score = 72
        mock_row.grade = "Good"
        mock_row.output_score = 0.78
        mock_row.improvements_summary = "Add constraints"
        mock_row.distance = 0.15

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.embeddings.service.generate_embedding", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_embedding

            results = await find_similar_evaluations(
                session=mock_session,
                query_text="Write about dogs",
            )

            assert len(results) == 1
            assert results[0]["input_text"] == "Write about cats"
            assert results[0]["overall_score"] == 72
            assert results[0]["distance"] == 0.15

    @pytest.mark.asyncio
    async def test_empty_results(self):
        mock_embedding = [0.1] * 768
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.embeddings.service.generate_embedding", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_embedding

            results = await find_similar_evaluations(
                session=mock_session,
                query_text="something unique",
            )

            assert results == []

    @pytest.mark.asyncio
    async def test_uses_custom_limit_and_threshold(self):
        mock_embedding = [0.1] * 768
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.embeddings.service.generate_embedding", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_embedding

            results = await find_similar_evaluations(
                session=mock_session,
                query_text="test",
                limit=3,
                threshold=0.9,
            )

            # Verify the ORM query was executed and returned results
            mock_session.execute.assert_called_once()
            assert results == []
