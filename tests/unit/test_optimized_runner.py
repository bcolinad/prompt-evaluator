"""Unit tests for the optimized prompt runner node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.nodes.optimized_runner import run_optimized_prompt


class TestRunOptimizedPrompt:
    @pytest.mark.asyncio
    async def test_returns_optimized_outputs(self):
        mock_response = MagicMock()
        mock_response.content = "Optimized output result."

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("src.agent.nodes.optimized_runner.get_llm", return_value=mock_llm):
            state = {
                "rewritten_prompt": "Improved prompt text",
                "execution_count": 2,
                "session_id": "test",
            }
            result = await run_optimized_prompt(state)

        assert result["optimized_outputs"] is not None
        assert len(result["optimized_outputs"]) == 2
        assert result["optimized_output_summary"] is not None
        assert result["current_step"] == "optimized_output_generated"
        assert "messages" in result

    @pytest.mark.asyncio
    async def test_skips_when_no_rewritten_prompt(self):
        state = {"session_id": "test"}
        result = await run_optimized_prompt(state)

        assert result["optimized_outputs"] is None
        assert result["optimized_output_summary"] is None
        assert result["current_step"] == "optimized_output_generated"

    @pytest.mark.asyncio
    async def test_skips_when_empty_rewritten_prompt(self):
        state = {"rewritten_prompt": "", "session_id": "test"}
        result = await run_optimized_prompt(state)

        assert result["optimized_outputs"] is None
        assert result["optimized_output_summary"] is None

    @pytest.mark.asyncio
    async def test_defaults_to_two_executions(self):
        mock_response = MagicMock()
        mock_response.content = "Output"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("src.agent.nodes.optimized_runner.get_llm", return_value=mock_llm):
            state = {
                "rewritten_prompt": "Some prompt",
                "session_id": "test",
            }
            result = await run_optimized_prompt(state)

        assert len(result["optimized_outputs"]) == 2
        assert mock_llm.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_partial_failures(self):
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("First call failed")
            mock_resp = MagicMock()
            mock_resp.content = "Success on second call"
            return mock_resp

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=side_effect)

        with patch("src.agent.nodes.optimized_runner.get_llm", return_value=mock_llm):
            state = {
                "rewritten_prompt": "Test prompt",
                "execution_count": 2,
                "session_id": "test",
            }
            result = await run_optimized_prompt(state)

        outputs = result["optimized_outputs"]
        assert len(outputs) == 2
        # One should be an error, one should be success
        error_outputs = [o for o in outputs if o.startswith("[Error:")]
        success_outputs = [o for o in outputs if not o.startswith("[Error:")]
        assert len(error_outputs) == 1
        assert len(success_outputs) == 1

    @pytest.mark.asyncio
    async def test_respects_execution_count(self):
        mock_response = MagicMock()
        mock_response.content = "Output"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("src.agent.nodes.optimized_runner.get_llm", return_value=mock_llm):
            state = {
                "rewritten_prompt": "Prompt",
                "execution_count": 4,
                "session_id": "test",
            }
            result = await run_optimized_prompt(state)

        assert len(result["optimized_outputs"]) == 4
        assert mock_llm.ainvoke.call_count == 4
