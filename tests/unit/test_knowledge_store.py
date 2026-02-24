"""Unit tests for the RAG knowledge store."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.rag.knowledge_store import (
    _load_criteria_doc,
    _load_domain_configs,
    _load_knowledge_docs,
    retrieve_context,
    warmup_knowledge_store,
)


class TestLoadKnowledgeDocs:
    def test_loads_markdown_files(self):
        docs = _load_knowledge_docs()
        # We have tcrei_framework.md and scoring_guide.md
        assert len(docs) >= 2
        assert any("tcrei_framework" in d.metadata["source"] for d in docs)
        assert any("scoring_guide" in d.metadata["source"] for d in docs)

    def test_metadata_includes_type(self):
        docs = _load_knowledge_docs()
        for doc in docs:
            assert doc.metadata["type"] == "knowledge"

    def test_content_not_empty(self):
        docs = _load_knowledge_docs()
        for doc in docs:
            assert len(doc.page_content) > 100

    @patch("src.rag.knowledge_store._KNOWLEDGE_DIR", Path("/nonexistent/path"))
    def test_missing_directory_returns_empty(self):
        docs = _load_knowledge_docs()
        assert docs == []


class TestLoadCriteriaDoc:
    def test_loads_criteria(self):
        docs = _load_criteria_doc()
        assert len(docs) == 1
        assert "TASK" in docs[0].page_content
        assert "CONTEXT" in docs[0].page_content
        assert docs[0].metadata["type"] == "criteria"

    def test_includes_criteria_names(self):
        docs = _load_criteria_doc()
        content = docs[0].page_content
        assert "clear_action_verb" in content
        assert "background_provided" in content


class TestLoadDomainConfigs:
    def test_loads_yaml_files(self):
        docs = _load_domain_configs()
        # At least healthcare.yaml exists
        assert len(docs) >= 1
        assert docs[0].metadata["type"] == "domain_config"

    @patch("src.rag.knowledge_store._DOMAINS_DIR", Path("/nonexistent/path"))
    def test_missing_directory_returns_empty(self):
        docs = _load_domain_configs()
        assert docs == []


class TestRetrieveContext:
    @pytest.mark.asyncio
    async def test_returns_string(self):
        """Test that retrieve_context returns a string (may be empty if embeddings fail)."""
        # Mock the store to avoid needing real embeddings
        mock_doc = MagicMock()
        mock_doc.page_content = "Task dimension evaluates clear action verbs"
        mock_doc.metadata = {"source": "tcrei_framework.md"}

        mock_store = MagicMock()
        mock_store.similarity_search.return_value = [mock_doc]

        with patch("src.rag.knowledge_store._get_store", return_value=mock_store):
            result = await retrieve_context("Write a blog post about dogs")
            assert isinstance(result, str)
            assert "Task dimension" in result

    @pytest.mark.asyncio
    async def test_empty_results(self):
        mock_store = MagicMock()
        mock_store.similarity_search.return_value = []

        with patch("src.rag.knowledge_store._get_store", return_value=mock_store):
            result = await retrieve_context("random query")
            assert result == ""

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self):
        with patch("src.rag.knowledge_store._get_store", side_effect=RuntimeError("store broken")):
            result = await retrieve_context("test query")
            assert result == ""

    @pytest.mark.asyncio
    async def test_multiple_results_joined(self):
        docs = [
            MagicMock(page_content="Chunk 1 content", metadata={"source": "a.md"}),
            MagicMock(page_content="Chunk 2 content", metadata={"source": "b.md"}),
        ]

        mock_store = MagicMock()
        mock_store.similarity_search.return_value = docs

        with patch("src.rag.knowledge_store._get_store", return_value=mock_store):
            result = await retrieve_context("test query", top_k=2)
            assert "Chunk 1" in result
            assert "Chunk 2" in result
            assert "---" in result

    @pytest.mark.asyncio
    async def test_top_k_parameter_passed(self):
        mock_store = MagicMock()
        mock_store.similarity_search.return_value = []

        with patch("src.rag.knowledge_store._get_store", return_value=mock_store):
            await retrieve_context("test", top_k=5)
            mock_store.similarity_search.assert_called_once_with("test", k=5)


class TestWarmupKnowledgeStore:
    def test_calls_get_store(self):
        mock_store = MagicMock()
        with patch("src.rag.knowledge_store._get_store", return_value=mock_store) as mock:
            warmup_knowledge_store()
            mock.assert_called_once()

    def test_logs_success(self, caplog):
        mock_store = MagicMock()
        with patch("src.rag.knowledge_store._get_store", return_value=mock_store):
            with caplog.at_level(logging.INFO, logger="src.rag.knowledge_store"):
                warmup_knowledge_store()
        assert "Warming up RAG knowledge store" in caplog.text
        assert "RAG knowledge store ready" in caplog.text

    def test_graceful_on_failure(self, caplog):
        with patch(
            "src.rag.knowledge_store._get_store",
            side_effect=ConnectionError("Ollama unreachable"),
        ), caplog.at_level(logging.WARNING, logger="src.rag.knowledge_store"):
            warmup_knowledge_store()  # should NOT raise
        assert "RAG warmup failed" in caplog.text
        assert "Ollama unreachable" in caplog.text
