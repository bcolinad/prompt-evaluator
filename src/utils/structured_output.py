"""Structured output helper for reliable LLM response parsing.

Provides ``invoke_structured()`` which uses the best strategy per provider:

- **Gemini**: Skips ``with_structured_output()`` entirely — Gemini's JSON
  schema mode produces partial results (missing dimensions) and hallucinated
  repetitive text on complex nested schemas.  Instead, uses raw invocation
  with thinking enabled + JSON extraction + ``model_validate()``.
- **Other models** (Anthropic, OpenAI): Tries ``with_structured_output()``
  first (tool-use / function-calling), then falls back to JSON extraction.

Also provides ``invoke_plain_text()`` for cases where the response is raw
text (e.g. a rewritten prompt) rather than structured JSON.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _extract_json(content: str) -> str:
    """Extract JSON from LLM response, handling code blocks."""
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    brace_match = re.search(r"\{.*\}", content, re.DOTALL)
    if brace_match:
        return brace_match.group(0).strip()

    return content.strip()


def _extract_text_content(response: object) -> str:
    """Extract text from an LLM response, handling Gemini thinking model format.

    Gemini 2.5 thinking models may return ``response.content`` as a list of
    typed blocks like::

        [
            {"type": "thinking", "thinking": "...", "signature": "..."},
            {"type": "text", "text": "actual JSON here"},
        ]

    This helper extracts the actual text content regardless of format.
    """
    content = getattr(response, "content", None)
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    # Handle list of content blocks (Gemini thinking models)
    if isinstance(content, list):
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                # Prefer "text" blocks, skip "thinking" blocks
                if (block.get("type") == "text" and "text" in block) or (block.get("type") not in ("thinking",) and "text" in block):
                    text_parts.append(block["text"])
            elif isinstance(block, str):
                text_parts.append(block)
            elif hasattr(block, "text"):
                # Handle typed LangChain content block objects (not plain dicts)
                block_type = getattr(block, "type", "")
                if block_type != "thinking":
                    text_parts.append(str(block.text))
        if text_parts:
            return "\n".join(text_parts)
        logger.warning(
            "Response content is a list with %d blocks but no text content found",
            len(content),
        )
        return ""

    # Unknown format — coerce to string as last resort
    logger.warning(
        "Unexpected response.content type %s, coercing to string",
        type(content).__name__,
    )
    return str(content)


def _is_thinking_model(llm: BaseChatModel) -> bool:
    """Check if the LLM is a Gemini thinking model with active thinking budget."""
    try:
        thinking_budget = getattr(llm, "thinking_budget", None)
        return isinstance(thinking_budget, (int, float)) and thinking_budget > 0
    except (TypeError, AttributeError):
        return False


def _is_google_model(llm: BaseChatModel) -> bool:
    """Check if the LLM is a Google/Gemini model.

    Gemini's ``with_structured_output()`` uses JSON schema mode
    (``response_mime_type="application/json"``) which produces partial,
    incomplete results on complex nested schemas — e.g. returning only 1
    of 4 expected dimensions, or generating hallucinated repetitive text.

    The raw invoke + JSON parsing path works reliably for Gemini because
    the model can reason about the full prompt instructions.
    """
    module = type(llm).__module__ or ""
    return "google" in module.lower()


def _is_ollama_model(llm: BaseChatModel) -> bool:
    """Check if the LLM is an Ollama model.

    Currently Ollama uses the same structured output path as Anthropic
    (``with_structured_output()`` first, JSON fallback second).  This
    detector is ready so that if tool-calling proves unreliable for a
    specific Ollama model, a single guard can route it to JSON-only.
    """
    module = type(llm).__module__ or ""
    return "ollama" in module.lower()


def _is_empty_result(result: BaseModel, schema: type[BaseModel]) -> bool:
    """Check if a structured output result contains only default values.

    Gemini's JSON schema mode can return ``{}`` or minimal JSON that Pydantic
    fills with defaults. This produces technically valid but semantically
    empty results. We detect this by comparing the result to a fresh default
    instance of the schema.

    Args:
        result: The parsed model instance to check.
        schema: The Pydantic model class used for parsing.

    Returns:
        True if the result is identical to an all-defaults instance.
    """
    try:
        return result.model_dump() == schema().model_dump()
    except Exception:
        return False


async def _invoke_json_fallback(
    llm: BaseChatModel,
    prompt: ChatPromptTemplate,
    variables: dict,
    schema: type[T],
) -> T | None:
    """Invoke an LLM and parse the response as JSON.

    Uses raw invocation (no JSON schema constraint) so the model can
    reason freely about the prompt, then extracts JSON from the text
    response and validates it against the Pydantic schema.

    Args:
        llm: The LangChain chat model instance.
        prompt: The chat prompt template to use.
        variables: Template variables to pass to the prompt.
        schema: The Pydantic model class defining the expected response shape.

    Returns:
        A validated instance of ``schema``, or ``None`` if parsing fails.
    """
    content = ""
    try:
        chain = prompt | llm
        response = await chain.ainvoke(variables)
        content = _extract_text_content(response)

        if not content:
            logger.warning(
                "Empty text content extracted from response for %s", schema.__name__
            )
            return None

        # Detect likely truncation
        stripped = content.rstrip()
        if stripped and stripped[-1] not in ("}", "]", "`"):
            logger.warning(
                "Response for %s appears truncated (length=%d, ends_with=%r). "
                "Consider increasing LLM_MAX_TOKENS.",
                schema.__name__,
                len(content),
                stripped[-20:] if len(stripped) >= 20 else stripped,
            )

        json_str = _extract_json(content)
        data = json.loads(json_str)
        return schema.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning(
            "JSON parsing failed for %s (response_length=%d): %s",
            schema.__name__,
            len(content),
            exc,
        )
    except Exception as exc:
        logger.warning("Unexpected error in JSON parsing for %s: %s", schema.__name__, exc)

    return None


async def invoke_structured(
    llm: BaseChatModel,
    prompt: ChatPromptTemplate,
    variables: dict,
    schema: type[T],
) -> T | None:
    """Invoke an LLM with structured output, using the best strategy per provider.

    **Google/Gemini models**: Skips ``with_structured_output()`` entirely.
    Gemini's JSON schema mode produces partial results on complex schemas
    (e.g. 1 of 4 dimensions, hallucinated repetitive text). Instead, uses
    raw invocation with thinking enabled + JSON extraction, which works
    reliably.

    **Other models** (Anthropic, OpenAI): Tries ``with_structured_output()``
    first (tool-use/function-calling mode, which works well), then falls
    back to JSON extraction on failure.

    Args:
        llm: The LangChain chat model instance.
        prompt: The chat prompt template to use.
        variables: Template variables to pass to the prompt.
        schema: The Pydantic model class defining the expected response shape.

    Returns:
        A validated instance of ``schema``, or ``None`` if all parsing fails.
    """
    # Google/Gemini: skip with_structured_output() — JSON schema mode is
    # unreliable for complex nested schemas. Go straight to raw invoke +
    # JSON parsing, which produces complete results.
    if _is_google_model(llm):
        logger.debug(
            "Google model detected — using raw JSON parsing for %s "
            "(skipping with_structured_output which produces partial results)",
            schema.__name__,
        )
        return await _invoke_json_fallback(llm, prompt, variables, schema)

    # Non-Google models: try native structured output first
    try:
        structured_llm = llm.with_structured_output(schema)
        chain = prompt | structured_llm
        result = await chain.ainvoke(variables)
        if isinstance(result, schema):
            if _is_empty_result(result, schema):
                logger.warning(
                    "Structured output for %s returned all-default values, "
                    "falling back to raw JSON parsing.",
                    schema.__name__,
                )
            else:
                return result
        elif isinstance(result, dict):
            validated = schema.model_validate(result)
            if not _is_empty_result(validated, schema):
                return validated
            logger.warning(
                "Structured output dict for %s was all-defaults, falling back to JSON",
                schema.__name__,
            )
        else:
            logger.warning(
                "Structured output for %s returned unexpected type %s (value: %r), "
                "falling back to JSON",
                schema.__name__,
                type(result).__name__,
                result,
            )
    except (NotImplementedError, TypeError, AttributeError) as exc:
        logger.debug("Structured output not supported, falling back to JSON: %s", exc)
    except Exception as exc:
        logger.warning("Structured output failed, falling back to JSON: %s", exc)

    # Fallback: raw invocation + JSON extraction
    return await _invoke_json_fallback(llm, prompt, variables, schema)


async def invoke_plain_text(
    llm: BaseChatModel,
    prompt: ChatPromptTemplate,
    variables: dict,
) -> str | None:
    """Invoke an LLM and return the raw text response (no JSON parsing).

    Useful when the expected output is free-form text (e.g. a rewritten
    prompt) rather than structured JSON.  A partial/truncated response is
    still returned as-is — the caller decides if it's acceptable.

    Args:
        llm: The LangChain chat model instance.
        prompt: The chat prompt template to use.
        variables: Template variables to pass to the prompt.

    Returns:
        The extracted text content, or ``None`` if the call fails entirely.
    """
    try:
        chain = prompt | llm
        response = await chain.ainvoke(variables)
        content = _extract_text_content(response)
        return content.strip() if content else None
    except Exception as exc:
        logger.warning("Plain text invocation failed: %s", exc)
        return None
