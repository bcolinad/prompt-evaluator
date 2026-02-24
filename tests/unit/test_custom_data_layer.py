"""Unit tests for the custom data layer with thread deletion cleanup."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.utils.custom_data_layer import CustomDataLayer


@pytest.fixture
def data_layer():
    """Create a CustomDataLayer with mocked internals."""
    with patch.object(CustomDataLayer, "__init__", lambda self: None):
        layer = CustomDataLayer.__new__(CustomDataLayer)
        layer.execute_query = AsyncMock(return_value=[])
        layer.storage_client = None
        return layer


class TestCustomDataLayerDeleteThread:
    @pytest.mark.asyncio
    async def test_delete_thread_cleans_app_tables(self, data_layer):
        """Verify DELETE queries are issued for both app tables."""
        with patch(
            "chainlit.data.chainlit_data_layer.ChainlitDataLayer.delete_thread",
            new_callable=AsyncMock,
        ) as mock_super:
            await data_layer.delete_thread("thread-abc-123")

        # Should have 2 app-table DELETEs + whatever super does
        calls = data_layer.execute_query.call_args_list
        queries = [c.args[0] for c in calls]

        assert any("conversation_embeddings" in q for q in queries)
        assert any("evaluations" in q for q in queries)
        mock_super.assert_awaited_once_with("thread-abc-123")

    @pytest.mark.asyncio
    async def test_delete_thread_proceeds_on_cleanup_failure(self, data_layer):
        """Exception in app cleanup doesn't block parent delete_thread."""
        data_layer.execute_query = AsyncMock(side_effect=Exception("DB error"))

        with patch(
            "chainlit.data.chainlit_data_layer.ChainlitDataLayer.delete_thread",
            new_callable=AsyncMock,
        ) as mock_super:
            await data_layer.delete_thread("thread-xyz")

        # Parent delete should still be called
        mock_super.assert_awaited_once_with("thread-xyz")

    @pytest.mark.asyncio
    async def test_delete_thread_calls_super(self, data_layer):
        """Parent delete_thread is always called."""
        with patch(
            "chainlit.data.chainlit_data_layer.ChainlitDataLayer.delete_thread",
            new_callable=AsyncMock,
        ) as mock_super:
            await data_layer.delete_thread("thread-123")

        mock_super.assert_awaited_once_with("thread-123")
