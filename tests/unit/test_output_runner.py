"""Unit tests for the output runner node (multi-execution)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.nodes.output_runner import (
    _format_multi_output,
    _run_n_times,
    run_prompt_for_output,
)


class TestRunNTimes:
    @pytest.mark.asyncio
    async def test_runs_n_times(self):
        mock_response = MagicMock()
        mock_response.content = "Output text"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        results = await _run_n_times(mock_llm, "test prompt", 3)
        assert len(results) == 3
        assert mock_llm.ainvoke.call_count == 3

    @pytest.mark.asyncio
    async def test_handles_partial_failures(self):
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Second call failed")
            mock_resp = MagicMock()
            mock_resp.content = f"Output {call_count}"
            return mock_resp

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=side_effect)

        results = await _run_n_times(mock_llm, "test prompt", 3)
        assert len(results) == 3
        error_results = [r for r in results if r.startswith("[Error:")]
        assert len(error_results) == 1


class TestFormatMultiOutput:
    def test_single_output(self):
        result = _format_multi_output(["Single output"])
        assert result == "Single output"

    def test_multiple_outputs(self):
        result = _format_multi_output(["Output 1", "Output 2"])
        assert "--- Run 1 ---" in result
        assert "--- Run 2 ---" in result
        assert "Output 1" in result
        assert "Output 2" in result


class TestRunPromptForOutput:
    @pytest.mark.asyncio
    async def test_returns_llm_output_and_original_outputs(self):
        mock_response = MagicMock()
        mock_response.content = "Dogs are wonderful companions."

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("src.agent.nodes.output_runner.get_llm", return_value=mock_llm):
            state = {"input_text": "Write about dogs", "execution_count": 2, "session_id": "test"}
            result = await run_prompt_for_output(state)

            assert result["llm_output"] is not None
            assert result["original_outputs"] is not None
            assert len(result["original_outputs"]) == 2
            assert result["original_output_summary"] is not None
            assert result["current_step"] == "output_generated"
            assert "messages" in result

    @pytest.mark.asyncio
    async def test_defaults_to_two_executions(self):
        mock_response = MagicMock()
        mock_response.content = "Output"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("src.agent.nodes.output_runner.get_llm", return_value=mock_llm):
            state = {"input_text": "Test", "session_id": "test"}
            result = await run_prompt_for_output(state)

            assert len(result["original_outputs"]) == 2
            assert mock_llm.ainvoke.call_count == 2

    @pytest.mark.asyncio
    async def test_respects_execution_count(self):
        mock_response = MagicMock()
        mock_response.content = "Output"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("src.agent.nodes.output_runner.get_llm", return_value=mock_llm):
            state = {"input_text": "Test", "execution_count": 4, "session_id": "test"}
            result = await run_prompt_for_output(state)

            assert len(result["original_outputs"]) == 4
            assert mock_llm.ainvoke.call_count == 4

    @pytest.mark.asyncio
    async def test_handles_llm_exception(self):
        """Test that LLM errors are caught and produce error content."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("API timeout"))

        with patch("src.agent.nodes.output_runner.get_llm", return_value=mock_llm):
            state = {"input_text": "Test prompt", "execution_count": 2, "session_id": "test"}
            result = await run_prompt_for_output(state)

            assert result["original_outputs"] is not None
            # All outputs should be error strings
            for output in result["original_outputs"]:
                assert "[Error:" in output

    @pytest.mark.asyncio
    async def test_handles_non_string_content(self):
        mock_response = MagicMock()
        mock_response.content = ["chunk1", "chunk2"]

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("src.agent.nodes.output_runner.get_llm", return_value=mock_llm):
            state = {"input_text": "Test", "execution_count": 1, "session_id": "test"}
            result = await run_prompt_for_output(state)

            assert isinstance(result["llm_output"], str)
