"""Chat message handler — streaming LLM conversation with thinking display."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

import chainlit as cl
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from src.config import get_settings
from src.ui.profiles import (
    _DOCUMENT_EXTENSIONS,
    _IMAGE_EXTENSIONS,
    _MAX_DOCUMENT_SIZE,
    _MAX_TEXT_FILE_SIZE,
    _TEXT_FILE_EXTENSIONS,
)

logger = logging.getLogger(__name__)


def _extract_thinking_and_text(content: Any) -> tuple[str, str]:
    """Extract thinking/reasoning blocks and text from LLM response content.

    Handles both string content (simple responses) and list content
    (responses with thinking blocks from Anthropic or Google).

    Args:
        content: The ``content`` attribute from an LLM response. May be a
            plain string or a list of typed content blocks.

    Returns:
        Tuple of (thinking_text, response_text). Either may be empty.
    """
    if isinstance(content, str):
        return "", content

    if not isinstance(content, list):
        return "", str(content)

    thinking_parts: list[str] = []
    text_parts: list[str] = []

    for block in content:
        # Handle dict-style blocks (Google Gemini)
        if isinstance(block, dict):
            block_type = block.get("type", "")
            block_text = block.get("text", "")
            if block_type == "thinking":
                thinking_parts.append(block_text)
            else:
                text_parts.append(block_text)
        # Handle typed objects (Anthropic)
        elif hasattr(block, "type"):
            block_type = getattr(block, "type", "")
            block_text = getattr(block, "text", "")
            if block_type == "thinking":
                thinking_parts.append(block_text)
            elif block_type == "text":
                text_parts.append(block_text)

    return "\n".join(thinking_parts), "\n".join(text_parts)


def _extract_chunk_deltas(content: Any) -> tuple[str, str]:
    """Extract thinking/text deltas from a single AIMessageChunk during streaming.

    Similar to ``_extract_thinking_and_text()`` but designed for individual
    streaming chunks rather than complete responses.

    Args:
        content: The ``content`` attribute from an ``AIMessageChunk``. May be
            a plain string, a list of dict blocks, or a list of typed objects.

    Returns:
        Tuple of (thinking_delta, text_delta). Either may be empty.
    """
    if content is None or content == "":
        return "", ""

    if isinstance(content, str):
        return "", content

    if not isinstance(content, list):
        return "", str(content)

    thinking_parts: list[str] = []
    text_parts: list[str] = []

    for block in content:
        if isinstance(block, dict):
            block_type = block.get("type", "")
            if block_type == "thinking":
                thinking_parts.append(
                    block.get("thinking", "") or block.get("text", "")
                )
            else:
                text_parts.append(block.get("text", ""))
        elif hasattr(block, "type"):
            block_type = getattr(block, "type", "")
            if block_type == "thinking":
                thinking_parts.append(
                    getattr(block, "thinking", "") or getattr(block, "text", "")
                )
            elif block_type == "text":
                text_parts.append(getattr(block, "text", ""))

    return "".join(thinking_parts), "".join(text_parts)


def _process_attachments(
    elements: list[Any],
) -> tuple[str, list[dict[str, Any]], list[tuple[Path, str]]]:
    """Process file attachments from a Chainlit message.

    Reads text files, encodes images for multimodal LLM messages, and
    identifies document files for document processing pipeline.

    Args:
        elements: List of ``cl.Element`` objects from the user message.

    Returns:
        Tuple of (text_prefix, image_blocks, document_paths):
        - text_prefix: Markdown code-fenced content from text files
        - image_blocks: Base64-encoded image content blocks for LangChain
        - document_paths: List of (file_path, original_filename) tuples for documents
    """

    text_prefix_parts: list[str] = []
    image_blocks: list[dict[str, Any]] = []
    document_paths: list[tuple[Path, str]] = []

    if not elements:
        return "", [], []

    for element in elements:
        name = getattr(element, "name", None) or ""
        path = getattr(element, "path", None)
        if not path:
            continue

        file_path = Path(path)
        suffix = file_path.suffix.lower()

        # Check for document types first (PDF, DOCX, XLSX, PPTX, CSV)
        if suffix in _DOCUMENT_EXTENSIONS:
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            if size > _MAX_DOCUMENT_SIZE:
                max_mb = _MAX_DOCUMENT_SIZE // (1024 * 1024)
                text_prefix_parts.append(
                    f"*Skipped `{name}` — exceeds {max_mb}MB document limit.*\n"
                )
                continue
            document_paths.append((file_path, name or file_path.name))

        elif suffix in _TEXT_FILE_EXTENSIONS:
            # Check file size
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            if size > _MAX_TEXT_FILE_SIZE:
                text_prefix_parts.append(
                    f"*Skipped `{name}` — exceeds {_MAX_TEXT_FILE_SIZE // 1024}KB limit.*\n"
                )
                continue
            try:
                file_content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lang = suffix.lstrip(".")
            text_prefix_parts.append(
                f"**Attached file: `{name}`**\n```{lang}\n{file_content}\n```\n"
            )

        elif suffix in _IMAGE_EXTENSIONS:
            try:
                image_bytes = file_path.read_bytes()
            except OSError:
                continue
            b64 = base64.b64encode(image_bytes).decode("utf-8")
            media_type = (
                "image/jpeg" if suffix in {".jpg", ".jpeg"}
                else f"image/{suffix.lstrip('.')}"
            )
            image_blocks.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{b64}",
                },
            })

        else:
            text_prefix_parts.append(
                f"*Skipped `{name}` — unsupported file type (`{suffix}`).*\n"
            )

    return "\n".join(text_prefix_parts), image_blocks, document_paths


def _get_chat_llm(provider: str) -> BaseChatModel:
    """Create an LLM instance configured for conversational chat.

    Unlike the evaluation LLM (which uses temperature=0.0), chat LLMs
    use higher temperatures for more natural conversation. Anthropic
    requires temperature=1.0 when extended thinking is enabled.

    Args:
        provider: ``"google"``, ``"anthropic"``, or ``"ollama"``.

    Returns:
        A configured ``BaseChatModel`` instance.

    Raises:
        RuntimeError: If the requested provider cannot be initialized.
    """
    settings = get_settings()

    if provider == "google":

        key_path = Path(__file__).resolve().parent.parent / "agent" / "nodes" / "google-key.json"
        if key_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_path)

        return ChatGoogleGenerativeAI(
            model=settings.google_model,
            project=settings.google_project,
            location=settings.google_location,
            vertexai=True,
            temperature=0.7,
            max_output_tokens=settings.llm_max_tokens,
            thinking_budget=settings.google_thinking_budget,
            timeout=settings.llm_request_timeout,
        )

    if provider == "ollama":
        return ChatOllama(
            model=settings.ollama_chat_model,
            base_url=settings.ollama_base_url,
            temperature=0.7,
            num_predict=settings.ollama_num_predict,
            timeout=settings.ollama_request_timeout,
        )

    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=1.0,
        max_tokens=settings.llm_max_tokens,
        thinking={
            "type": "enabled",
            "budget_tokens": 4096,
        },
    )


async def _handle_chat_message(
    user_input: str,
    image_blocks: list[dict[str, Any]] | None = None,
) -> None:
    """Handle a chat message with live token streaming.

    Streams the LLM response token-by-token, displaying thinking in a
    collapsible ``cl.Step`` and the response text in a ``cl.Message``.
    Supports multimodal messages when ``image_blocks`` are provided.

    Args:
        user_input: The user's message text (may include file content prefix).
        image_blocks: Optional list of base64-encoded image content blocks
            for multimodal messages.
    """
    provider: str = cl.user_session.get("chat_provider", "google")  # type: ignore[no-untyped-call]
    chat_history: list[dict[str, str]] = cl.user_session.get("chat_history", [])  # type: ignore[no-untyped-call]

    # Build messages for the LLM
    messages: list[Any] = []
    for msg in chat_history:
        if msg["role"] == "human":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    # Build the current user message (multimodal if images attached)
    if image_blocks:
        if provider == "ollama":
            await cl.Message(
                content="**Note:** Image attachments may not work with all Ollama models. "
                "Only vision-capable models (e.g., `llava`, `llama3.2-vision`) support images. "
                "The image will be sent, but the model may ignore it or produce errors.",
            ).send()
        content_blocks: list[dict[str, Any]] = [{"type": "text", "text": user_input}]
        content_blocks.extend(image_blocks)
        messages.append(HumanMessage(content=content_blocks))
    else:
        messages.append(HumanMessage(content=user_input))

    try:
        llm = _get_chat_llm(provider)

        # Show a visible status message so the user knows the model is working.
        # This replaces an invisible typing indicator with clear text feedback.
        provider_label = {"google": "Gemini", "anthropic": "Claude", "ollama": "Ollama"}.get(provider, provider)
        status_msg = cl.Message(  # type: ignore[no-untyped-call]
            content=f"*{provider_label} is thinking...*",
        )
        await status_msg.send()

        thinking_step: cl.Step | None = None
        response_msg: cl.Message | None = None
        full_thinking = ""
        full_text = ""
        is_streaming_thinking = False
        chunk_count = 0

        async for chunk in llm.astream(messages):
            chunk_count += 1
            thinking_delta, text_delta = _extract_chunk_deltas(chunk.content)

            logger.debug(
                "Chat stream chunk #%d: thinking=%d chars, text=%d chars, raw_type=%s",
                chunk_count,
                len(thinking_delta),
                len(text_delta),
                type(chunk.content).__name__,
            )

            # Stream thinking into a collapsible Step
            if thinking_delta:
                if not is_streaming_thinking:
                    thinking_step = cl.Step(name="Model Thinking")  # type: ignore[no-untyped-call]
                    await thinking_step.send()  # type: ignore[union-attr]
                    is_streaming_thinking = True
                    # Update status so user sees thinking is active
                    status_msg.content = f"*{provider_label} is reasoning...*"
                    await status_msg.update()  # type: ignore[no-untyped-call]
                await thinking_step.stream_token(thinking_delta)  # type: ignore[union-attr]
                full_thinking += thinking_delta

            # Stream text into the response Message
            if text_delta:
                if is_streaming_thinking and thinking_step is not None:
                    # Finalize thinking step before starting text
                    await thinking_step.update()  # type: ignore[union-attr]
                    is_streaming_thinking = False
                if response_msg is None:
                    # Remove the status message and start streaming the real response
                    await status_msg.remove()  # type: ignore[no-untyped-call]
                    response_msg = cl.Message(content="")  # type: ignore[no-untyped-call]
                    await response_msg.send()
                await response_msg.stream_token(text_delta)
                full_text += text_delta

        logger.info("Chat stream completed: %d chunks, %d thinking chars, %d text chars",
                     chunk_count, len(full_thinking), len(full_text))

        # Finalize any open thinking step
        if is_streaming_thinking and thinking_step is not None:
            await thinking_step.update()  # type: ignore[union-attr]

        # Finalize the response message
        if response_msg is not None and full_text:
            await response_msg.update()  # type: ignore[no-untyped-call]
        elif full_text:
            # Text came but response_msg wasn't created (shouldn't happen)
            await status_msg.remove()  # type: ignore[no-untyped-call]
            await cl.Message(content=full_text).send()  # type: ignore[no-untyped-call]
        else:
            # No text was streamed — update status to show fallback
            status_msg.content = "(No response text)"
            await status_msg.update()  # type: ignore[no-untyped-call]

        # Update chat history
        chat_history.append({"role": "human", "content": user_input})
        chat_history.append({"role": "assistant", "content": full_text or ""})
        cl.user_session.set("chat_history", chat_history)  # type: ignore[no-untyped-call]

    except Exception as e:
        logger.exception("Chat message failed: %s", e)
        await cl.Message(  # type: ignore[no-untyped-call]
            content=f"Error communicating with the model: {e}"
        ).send()
