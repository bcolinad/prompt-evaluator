"""Unit tests for the structured output helper."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.evaluator.llm_schemas import AnalysisLLMResponse, FollowupLLMResponse
from src.utils.structured_output import (
    _extract_json,
    _extract_text_content,
    _is_empty_result,
    _is_google_model,
    _is_ollama_model,
    _is_thinking_model,
    invoke_structured,
)


class TestExtractJson:
    def test_json_code_block(self):
        content = '```json\n{"key": "value"}\n```'
        assert _extract_json(content) == '{"key": "value"}'

    def test_plain_code_block(self):
        content = '```\n{"key": "value"}\n```'
        assert _extract_json(content) == '{"key": "value"}'

    def test_bare_json(self):
        content = '{"key": "value"}'
        assert _extract_json(content) == '{"key": "value"}'

    def test_json_with_surrounding_text(self):
        content = 'Here is the result:\n{"key": "value"}\nDone.'
        assert _extract_json(content) == '{"key": "value"}'

    def test_no_json(self):
        content = "No JSON here"
        assert _extract_json(content) == "No JSON here"

    def test_case_insensitive_code_block(self):
        content = '```JSON\n{"key": "value"}\n```'
        assert _extract_json(content) == '{"key": "value"}'


class TestExtractTextContent:
    def test_string_content(self):
        response = MagicMock()
        response.content = '{"key": "value"}'
        assert _extract_text_content(response) == '{"key": "value"}'

    def test_list_with_text_block(self):
        """Gemini thinking model returns list with text block."""
        response = MagicMock()
        response.content = [
            {"type": "thinking", "thinking": "Let me think...", "signature": "abc"},
            {"type": "text", "text": '{"intent": "explain", "response": "hi"}'},
        ]
        result = _extract_text_content(response)
        assert result == '{"intent": "explain", "response": "hi"}'

    def test_list_with_multiple_text_blocks(self):
        response = MagicMock()
        response.content = [
            {"type": "text", "text": "part1"},
            {"type": "text", "text": "part2"},
        ]
        assert _extract_text_content(response) == "part1\npart2"

    def test_list_with_only_thinking_blocks(self):
        """All thinking blocks, no text — returns empty string."""
        response = MagicMock()
        response.content = [
            {"type": "thinking", "thinking": "...", "signature": "abc"},
        ]
        assert _extract_text_content(response) == ""

    def test_list_with_string_blocks(self):
        response = MagicMock()
        response.content = ["hello", "world"]
        assert _extract_text_content(response) == "hello\nworld"

    def test_none_content(self):
        response = MagicMock()
        response.content = None
        assert _extract_text_content(response) == ""

    def test_no_content_attribute(self):
        response = object()
        assert _extract_text_content(response) == ""

    def test_unexpected_type_coerced(self):
        response = MagicMock()
        response.content = 12345
        assert _extract_text_content(response) == "12345"

    def test_empty_list(self):
        response = MagicMock()
        response.content = []
        assert _extract_text_content(response) == ""

    def test_list_skips_thinking_keeps_text(self):
        """Verify thinking blocks are skipped and text blocks are kept."""
        response = MagicMock()
        response.content = [
            {"type": "thinking", "thinking": "step 1"},
            {"type": "thinking", "thinking": "step 2"},
            {"type": "text", "text": '{"result": true}'},
        ]
        assert _extract_text_content(response) == '{"result": true}'


class TestIsThinkingModel:
    def test_gemini_with_budget(self):
        llm = MagicMock()
        llm.thinking_budget = 2048
        assert _is_thinking_model(llm) is True

    def test_gemini_with_zero_budget(self):
        llm = MagicMock()
        llm.thinking_budget = 0
        assert _is_thinking_model(llm) is False

    def test_gemini_with_none_budget(self):
        llm = MagicMock()
        llm.thinking_budget = None
        assert _is_thinking_model(llm) is False

    def test_non_gemini_model(self):
        llm = MagicMock(spec=[])  # No attributes
        assert _is_thinking_model(llm) is False


class TestIsGoogleModel:
    def test_google_genai_module(self):
        """ChatGoogleGenerativeAI should be detected as Google model."""
        llm = MagicMock()
        type(llm).__module__ = "langchain_google_genai.chat_models"
        assert _is_google_model(llm) is True

    def test_google_vertexai_module(self):
        """Vertex AI models should be detected as Google model."""
        llm = MagicMock()
        type(llm).__module__ = "langchain_google_vertexai.chat_models"
        assert _is_google_model(llm) is True

    def test_anthropic_module(self):
        """Anthropic models should NOT be detected as Google."""
        llm = MagicMock()
        type(llm).__module__ = "langchain_anthropic.chat_models"
        assert _is_google_model(llm) is False

    def test_no_module(self):
        """Models with no module should NOT be detected as Google."""
        llm = MagicMock(spec=[])
        assert _is_google_model(llm) is False


class TestIsOllamaModel:
    def test_ollama_module_detected(self):
        """ChatOllama should be detected as Ollama model."""
        llm = MagicMock()
        type(llm).__module__ = "langchain_ollama.chat_models"
        assert _is_ollama_model(llm) is True

    def test_anthropic_module_not_detected(self):
        """Anthropic models should NOT be detected as Ollama."""
        llm = MagicMock()
        type(llm).__module__ = "langchain_anthropic.chat_models"
        assert _is_ollama_model(llm) is False

    def test_google_module_not_detected(self):
        """Google models should NOT be detected as Ollama."""
        llm = MagicMock()
        type(llm).__module__ = "langchain_google_genai.chat_models"
        assert _is_ollama_model(llm) is False

    def test_no_module(self):
        """Models with no module should NOT be detected as Ollama."""
        llm = MagicMock(spec=[])
        assert _is_ollama_model(llm) is False

    def test_ollama_uses_structured_output_path(self):
        """Ollama model should use with_structured_output (same as non-Google)."""
        # Ollama is NOT a Google model, so it takes the non-Google path
        llm = MagicMock()
        type(llm).__module__ = "langchain_ollama.chat_models"
        assert _is_google_model(llm) is False


class TestInvokeStructured:
    @pytest.mark.asyncio
    async def test_structured_output_success(self):
        """Test that native structured output works when supported."""
        expected = FollowupLLMResponse(intent="explain", response="Details here")

        mock_structured_llm = AsyncMock()
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=expected)

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured_llm)

        result = await invoke_structured(mock_llm, mock_prompt, {"x": "y"}, FollowupLLMResponse)
        assert result is not None
        assert result.intent == "explain"
        assert result.response == "Details here"

    @pytest.mark.asyncio
    async def test_structured_output_returns_dict(self):
        """Test that a dict return from structured output is validated."""
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value={"intent": "explain", "response": "hi"})

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(return_value=MagicMock())

        result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)
        assert result is not None
        assert result.intent == "explain"

    @pytest.mark.asyncio
    async def test_fallback_to_json_parsing(self):
        """Test fallback to JSON parsing when structured output fails."""
        mock_prompt = MagicMock()

        # Make structured output fail
        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(side_effect=NotImplementedError("not supported"))

        # Make raw invocation succeed with JSON in response
        mock_response = MagicMock()
        mock_response.content = '{"intent": "re_evaluate", "response": "Re-evaluating", "new_prompt": "new", "new_rewrite": null, "new_mode": null}'

        mock_raw_chain = AsyncMock()
        mock_raw_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_raw_chain)

        result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)
        assert result is not None
        assert result.intent == "re_evaluate"
        assert result.new_prompt == "new"

    @pytest.mark.asyncio
    async def test_fallback_with_code_block(self):
        """Test fallback handles JSON in code blocks."""
        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(side_effect=NotImplementedError())

        mock_response = MagicMock()
        mock_response.content = '```json\n{"intent": "explain", "response": "test"}\n```'

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)
        assert result is not None
        assert result.intent == "explain"

    @pytest.mark.asyncio
    async def test_total_failure_returns_none(self):
        """Test that None is returned when all parsing attempts fail."""
        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(side_effect=NotImplementedError())

        mock_response = MagicMock()
        mock_response.content = "This is not JSON at all"

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)
        assert result is None

    @pytest.mark.asyncio
    async def test_structured_output_general_exception_triggers_fallback(self):
        """Test that a general exception in structured output triggers fallback."""
        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(side_effect=RuntimeError("unexpected"))

        mock_response = MagicMock()
        mock_response.content = '{"intent": "explain", "response": "fallback worked"}'

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)
        assert result is not None
        assert result.response == "fallback worked"

    @pytest.mark.asyncio
    async def test_analysis_schema(self):
        """Test with AnalysisLLMResponse schema."""
        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(side_effect=NotImplementedError())

        mock_response = MagicMock()
        mock_response.content = '''{
            "dimensions": {
                "task": {"score": 75, "sub_criteria": [{"name": "verb", "found": true, "detail": "ok"}]},
                "context": {"score": 50, "sub_criteria": []}
            },
            "tcrei_flags": {"task": true, "context": false, "references": false, "evaluate": false, "iterate": false}
        }'''

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = await invoke_structured(mock_llm, mock_prompt, {}, AnalysisLLMResponse)
        assert result is not None
        assert result.dimensions["task"].score == 75
        assert result.tcrei_flags.task is True

    @pytest.mark.asyncio
    async def test_logs_truncation_warning(self, caplog):
        """Test that a truncated response logs a warning with length info."""
        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(side_effect=NotImplementedError())

        # Simulate truncated response — ends mid-word, not with }, ], or `
        truncated_content = '{"intent": "explain", "response": "This is a very long text that got cu'
        mock_response = MagicMock()
        mock_response.content = truncated_content

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with caplog.at_level(logging.WARNING, logger="src.utils.structured_output"):
            await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)

        assert any("appears truncated" in msg for msg in caplog.messages)
        assert any(f"length={len(truncated_content)}" in msg for msg in caplog.messages)

    @pytest.mark.asyncio
    async def test_logs_response_length_on_parse_failure(self, caplog):
        """Test that JSON parse failure includes response_length in log."""
        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(side_effect=NotImplementedError())

        bad_content = "This is not JSON at all, just plain text response."
        mock_response = MagicMock()
        mock_response.content = bad_content

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with caplog.at_level(logging.WARNING, logger="src.utils.structured_output"):
            result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)

        assert result is None
        assert any(f"response_length={len(bad_content)}" in msg for msg in caplog.messages)

    @pytest.mark.asyncio
    async def test_gemini_thinking_list_content_fallback(self):
        """Test that Gemini thinking model list content is properly extracted."""
        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(side_effect=NotImplementedError())

        # Simulate Gemini thinking model response with list content
        mock_response = MagicMock()
        mock_response.content = [
            {"type": "thinking", "thinking": "Let me analyze...", "signature": "sig123"},
            {"type": "text", "text": '{"intent": "explain", "response": "from thinking model"}'},
        ]

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)
        assert result is not None
        assert result.intent == "explain"
        assert result.response == "from thinking model"

    @pytest.mark.asyncio
    async def test_google_model_skips_structured_output(self):
        """Google models should skip with_structured_output and use raw JSON parsing."""
        mock_prompt = MagicMock()

        # Make a mock that looks like a Google model
        mock_llm = MagicMock()
        type(mock_llm).__module__ = "langchain_google_genai.chat_models"

        # Raw invoke returns valid JSON
        mock_response = MagicMock()
        mock_response.content = '{"intent": "explain", "response": "from raw JSON"}'
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)
        assert result is not None
        assert result.intent == "explain"
        assert result.response == "from raw JSON"

        # with_structured_output should NEVER be called for Google models
        mock_llm.with_structured_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_google_model_uses_structured_output(self):
        """Non-Google models should try with_structured_output first."""
        expected = FollowupLLMResponse(intent="explain", response="direct output")

        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(return_value=MagicMock())

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=expected)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)
        assert result is not None
        assert result.intent == "explain"
        mock_llm.with_structured_output.assert_called_once_with(FollowupLLMResponse)

    @pytest.mark.asyncio
    async def test_structured_output_returns_none_logs_warning(self, caplog):
        """Test that Attempt 1 returning None/unexpected type logs a warning."""
        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])

        # Structured output returns None
        mock_structured = MagicMock()
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=None)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        # Attempt 2 succeeds
        mock_response = MagicMock()
        mock_response.content = '{"intent": "explain", "response": "ok"}'
        mock_raw_chain = AsyncMock()
        mock_raw_chain.ainvoke = AsyncMock(return_value=mock_response)

        # __or__ returns different chains for different calls
        call_count = 0
        def side_effect(other):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_chain
            return mock_raw_chain
        mock_prompt.__or__ = MagicMock(side_effect=side_effect)

        with caplog.at_level(logging.WARNING, logger="src.utils.structured_output"):
            result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)

        assert result is not None
        assert any("unexpected type" in msg for msg in caplog.messages)


class TestIsEmptyResult:
    """Tests for _is_empty_result — detects all-default Pydantic instances."""

    def test_empty_followup_is_detected(self):
        """A FollowupLLMResponse with all defaults should be detected as empty."""
        empty = FollowupLLMResponse()
        assert _is_empty_result(empty, FollowupLLMResponse) is True

    def test_populated_followup_is_not_empty(self):
        """A FollowupLLMResponse with real data should NOT be empty."""
        populated = FollowupLLMResponse(intent="re_evaluate", response="Try again")
        assert _is_empty_result(populated, FollowupLLMResponse) is False

    def test_empty_analysis_is_detected(self):
        """An AnalysisLLMResponse with all defaults should be detected as empty."""
        empty = AnalysisLLMResponse()
        assert _is_empty_result(empty, AnalysisLLMResponse) is True

    def test_populated_analysis_is_not_empty(self):
        """An AnalysisLLMResponse with at least one dimension should NOT be empty."""
        from src.evaluator.llm_schemas import DimensionLLMResponse

        populated = AnalysisLLMResponse(
            dimensions={"task": DimensionLLMResponse(score=75, sub_criteria=[])}
        )
        assert _is_empty_result(populated, AnalysisLLMResponse) is False

    def test_partial_defaults_still_detected(self):
        """A FollowupLLMResponse matching default intent but empty response is still all-defaults."""
        # "explain" is the default intent, "" is the default response
        partial = FollowupLLMResponse(intent="explain", response="")
        assert _is_empty_result(partial, FollowupLLMResponse) is True

    def test_single_changed_field_is_not_empty(self):
        """Changing even one field from default means it's not empty."""
        almost_default = FollowupLLMResponse(intent="explain", response="actual content")
        assert _is_empty_result(almost_default, FollowupLLMResponse) is False


class TestInvokeStructuredEmptyResultFallback:
    """Tests for the empty-result detection and fallback in invoke_structured."""

    @pytest.mark.asyncio
    async def test_empty_structured_result_falls_through_to_json(self, caplog):
        """When structured output returns all-default values (Gemini empty JSON),
        invoke_structured should fall through to the JSON fallback path."""
        empty_result = AnalysisLLMResponse()  # All defaults

        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])

        # Attempt 1: structured output returns empty (all-defaults)
        mock_structured = MagicMock()
        mock_chain_structured = AsyncMock()
        mock_chain_structured.ainvoke = AsyncMock(return_value=empty_result)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)

        # Attempt 2: JSON fallback returns real data

        real_json = '{"dimensions": {"task": {"score": 80, "sub_criteria": [{"name": "verb", "found": true, "detail": "ok"}]}}, "tcrei_flags": {"task": true, "context": false, "references": false, "evaluate": false, "iterate": false}}'
        mock_response = MagicMock()
        mock_response.content = real_json
        mock_chain_raw = AsyncMock()
        mock_chain_raw.ainvoke = AsyncMock(return_value=mock_response)

        call_count = 0
        def or_side_effect(other):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_chain_structured
            return mock_chain_raw
        mock_prompt.__or__ = MagicMock(side_effect=or_side_effect)

        with caplog.at_level(logging.WARNING, logger="src.utils.structured_output"):
            result = await invoke_structured(mock_llm, mock_prompt, {}, AnalysisLLMResponse)

        assert result is not None
        assert "task" in result.dimensions
        assert result.dimensions["task"].score == 80
        assert any("all-default values" in msg for msg in caplog.messages)

    @pytest.mark.asyncio
    async def test_empty_dict_result_falls_through_to_json(self, caplog):
        """When structured output returns an empty dict (Gemini {}),
        invoke_structured should detect all-defaults and fall through."""
        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])

        # Attempt 1: structured output returns empty dict
        mock_structured = MagicMock()
        mock_chain_structured = AsyncMock()
        mock_chain_structured.ainvoke = AsyncMock(return_value={})
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)

        # Attempt 2: JSON fallback returns real data
        mock_response = MagicMock()
        mock_response.content = '{"intent": "re_evaluate", "response": "Better prompt here"}'
        mock_chain_raw = AsyncMock()
        mock_chain_raw.ainvoke = AsyncMock(return_value=mock_response)

        call_count = 0
        def or_side_effect(other):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_chain_structured
            return mock_chain_raw
        mock_prompt.__or__ = MagicMock(side_effect=or_side_effect)

        with caplog.at_level(logging.WARNING, logger="src.utils.structured_output"):
            result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)

        assert result is not None
        assert result.intent == "re_evaluate"
        assert result.response == "Better prompt here"
        assert any("all-defaults" in msg for msg in caplog.messages)

    @pytest.mark.asyncio
    async def test_non_empty_structured_result_returned_directly(self):
        """When structured output returns a real populated result, it should
        be returned immediately without falling through to JSON."""
        real_result = FollowupLLMResponse(intent="re_evaluate", response="Real content")

        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])

        mock_structured = MagicMock()
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=real_result)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)

        assert result is not None
        assert result.intent == "re_evaluate"
        assert result.response == "Real content"

    @pytest.mark.asyncio
    async def test_google_model_uses_raw_json_directly(self, caplog):
        """Google models should skip structured output entirely and use raw JSON,
        which produces complete results with all dimensions."""
        mock_prompt = MagicMock()

        # Google model
        mock_llm = MagicMock()
        type(mock_llm).__module__ = "langchain_google_genai.chat_models"

        # Raw invoke returns complete JSON with all 4 dimensions
        real_json = '{"dimensions": {"task": {"score": 90, "sub_criteria": [{"name": "verb", "found": true, "detail": "ok"}]}, "context": {"score": 10, "sub_criteria": []}, "references": {"score": 10, "sub_criteria": []}, "constraints": {"score": 45, "sub_criteria": []}}, "tcrei_flags": {"task": true, "context": false, "references": false, "evaluate": false, "iterate": false}}'
        mock_response = MagicMock()
        mock_response.content = real_json
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        with caplog.at_level(logging.DEBUG, logger="src.utils.structured_output"):
            result = await invoke_structured(mock_llm, mock_prompt, {}, AnalysisLLMResponse)

        assert result is not None
        assert len(result.dimensions) == 4
        assert result.dimensions["task"].score == 90
        assert result.dimensions["context"].score == 10
        assert result.dimensions["constraints"].score == 45
        assert any("Google model detected" in msg for msg in caplog.messages)
        # with_structured_output should NOT be called
        mock_llm.with_structured_output.assert_not_called()

    @pytest.mark.asyncio
    async def test_google_model_with_thinking_content_blocks(self):
        """Google models with thinking enabled should extract text from content blocks."""
        mock_prompt = MagicMock()

        mock_llm = MagicMock()
        type(mock_llm).__module__ = "langchain_google_genai.chat_models"

        # Simulate thinking model response with list content
        thinking_block = MagicMock()
        thinking_block.type = "thinking"
        thinking_block.text = "Let me analyze this..."

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = '{"intent": "explain", "response": "From thinking model"}'

        mock_response = MagicMock()
        mock_response.content = [thinking_block, text_block]

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)
        assert result is not None
        assert result.intent == "explain"
        assert result.response == "From thinking model"

    @pytest.mark.asyncio
    async def test_typed_content_blocks_extraction(self):
        """Test that typed LangChain content block objects (not dicts) are handled."""
        mock_prompt = MagicMock()
        mock_llm = MagicMock(spec=[])
        mock_llm.with_structured_output = MagicMock(side_effect=NotImplementedError())

        # Simulate typed content blocks (like LangChain's AIMessageChunk parts)
        thinking_block = MagicMock()
        thinking_block.type = "thinking"
        thinking_block.text = "Let me think about this..."

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = '{"intent": "explain", "response": "From typed block"}'

        mock_response = MagicMock()
        mock_response.content = [thinking_block, text_block]

        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = await invoke_structured(mock_llm, mock_prompt, {}, FollowupLLMResponse)
        assert result is not None
        assert result.intent == "explain"
        assert result.response == "From typed block"
