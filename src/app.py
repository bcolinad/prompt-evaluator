"""Chainlit chat application — entry point for the Professional Prompt Shaper UI."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

load_dotenv()

import chainlit as cl
from chainlit.input_widget import Select

from src.config import get_settings
from src.evaluator import EvalMode, TaskType
from src.evaluator.example_prompts import get_example_for_task_type
from src.rag.knowledge_store import warmup_knowledge_store

# UI modules — used directly by Chainlit handlers below
from src.ui.audio_handler import transcribe_audio

# Backward-compat re-exports — tests import these from src.app
from src.ui.chat_handler import (  # noqa: F401
    _extract_chunk_deltas,
    _extract_thinking_and_text,
    _get_chat_llm,
    _handle_chat_message,
    _process_attachments,
)
from src.ui.evaluation_runner import (  # noqa: F401
    NODE_STEP_MAP,
    _extract_step_summary,
    _progress_bar,
    _run_evaluation,
)
from src.ui.profiles import (
    _CHAT_PROFILE_NAME,
    _DEFAULT_WELCOME,
    _PROFILE_TO_TASK_TYPE,
    _WELCOME_MESSAGES,
)
from src.ui.results_display import _send_recommendations, _send_results  # noqa: F401
from src.ui.thread_utils import _set_thread_name, increment_chat_counter
from src.utils.custom_data_layer import CustomDataLayer
from src.utils.example_formatter import format_example_markdown
from src.utils.local_storage import LocalStorageClient, mount_local_files_endpoint
from src.utils.logging_config import setup_logging

_boot = get_settings()
setup_logging(level=_boot.log_level, environment=_boot.app_env.value)

logger = logging.getLogger(__name__)

# Pre-load RAG knowledge store (documents + embeddings) before accepting requests
warmup_knowledge_store()

# Serve locally-stored files (HTML reports) via HTTP for chat history replay
mount_local_files_endpoint()

# ===== Data Layer (local file storage) ========================================

@cl.data_layer  # type: ignore[misc]
def get_data_layer():  # type: ignore[no-untyped-def]
    """Configure Chainlit data layer with local filesystem storage.

    Uses ``CustomDataLayer`` which extends ``ChainlitDataLayer`` to clean up
    app-owned tables (``evaluations``, ``conversation_embeddings``) when a
    Chainlit thread is deleted from the sidebar.
    """

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return None
    return CustomDataLayer(
        database_url=database_url,
        storage_client=LocalStorageClient(),
    )


# ===== Authentication ===========================================================

@cl.password_auth_callback  # type: ignore[misc]
async def auth_callback(username: str, password: str) -> cl.User | None:
    """Authenticate users.

    When auth is disabled, accepts any non-empty username.
    When enabled, validates against configured admin credentials.
    """
    settings = get_settings()
    if not settings.auth_enabled:
        return cl.User(identifier=username or "anonymous", metadata={"role": "user"})
    if username == settings.auth_admin_email and password == settings.auth_admin_password:
        return cl.User(identifier=username, metadata={"role": "admin"})
    return None


# ===== Chat Profiles (persistent task-type selector in header) ================

@cl.set_chat_profiles  # type: ignore[misc]
async def chat_profiles() -> list[cl.ChatProfile]:
    """Define the persistent task-type selector that appears in the Chainlit header."""
    return [
        cl.ChatProfile(
            name="General Task Prompts",
            markdown_description="Standard **T.C.R.E.I.** framework — evaluates Task, Context, References, "
            "Constraints and general output quality dimensions.",
            default=True,
        ),
        cl.ChatProfile(
            name="Email Creation Prompts",
            markdown_description="**Email-specific** criteria — evaluates tone/style, recipient clarity, "
            "email structure, purpose, audience fit, and conciseness.",
        ),
        cl.ChatProfile(
            name="Summarization Prompts",
            markdown_description="**Summarization-specific** criteria — evaluates source material, summary type, "
            "length constraints, information accuracy, source fidelity, and conciseness.",
        ),
        cl.ChatProfile(
            name="Coding Task Prompts",
            markdown_description="**Coding-specific** criteria — evaluates language/stack, requirements clarity, "
            "architecture guidance, code quality standards, error handling, and security.",
        ),
        cl.ChatProfile(
            name="Exam Interview Agent Prompts",
            markdown_description="**Assessment-specific** criteria — evaluates question design, difficulty calibration, "
            "rubric completeness, candidate profile, fairness safeguards, and coverage.",
        ),
        cl.ChatProfile(
            name="LinkedIn Professional Post Prompts",
            markdown_description="**LinkedIn-specific** criteria — evaluates post objective, writing voice, "
            "audience targeting, platform optimization, hook quality, and engagement potential.",
        ),
        cl.ChatProfile(
            name="Test your optimized prompts",
            markdown_description="**Direct chat** with Google Gemini , Anthropic Claude or Ollama Qwen 3 — switch providers and test your newly optimized prompts in real time."
            "via the settings widget. Includes thinking/reasoning display. No prompt evaluation, just conversation.",
        ),
    ]


# ===== Chainlit Handlers =====================================================

@cl.on_chat_resume  # type: ignore[misc]
async def on_chat_resume(thread: dict) -> None:
    """Restore session state when a user resumes a previous conversation.

    Chainlit calls this after the WebSocket authorization check passes.
    Without this handler, resumed threads lose session-level state (profile
    mode, task type, LLM provider, chat history) and behave unpredictably.

    Args:
        thread: The ``ThreadDict`` for the resumed thread, including metadata
            with ``chat_profile`` and ``chat_settings`` if previously stored.
    """
    metadata: dict = thread.get("metadata") or {}

    # Determine the profile that was active when this thread was created
    profile_name: str = metadata.get("chat_profile", "General Task Prompts")

    # Read authenticated user
    user = cl.user_session.get("user")  # type: ignore[no-untyped-call]
    user_id = user.identifier if user else "anonymous"
    cl.user_session.set("user_id", user_id)  # type: ignore[no-untyped-call]

    if profile_name == _CHAT_PROFILE_NAME:
        # Chat mode
        cl.user_session.set("profile_mode", "chat")  # type: ignore[no-untyped-call]
        cl.user_session.set("chat_provider", "google")  # type: ignore[no-untyped-call]
        cl.user_session.set("chat_history", [])  # type: ignore[no-untyped-call]
    else:
        # Evaluator mode
        cl.user_session.set("profile_mode", "evaluator")  # type: ignore[no-untyped-call]
        task_type = _PROFILE_TO_TASK_TYPE.get(profile_name, TaskType.GENERAL)
        cl.user_session.set("task_type", task_type)  # type: ignore[no-untyped-call]
        cl.user_session.set("llm_provider", "google")  # type: ignore[no-untyped-call]
        cl.user_session.set("execution_count", 2)  # type: ignore[no-untyped-call]

    cl.user_session.set("mode", EvalMode.PROMPT)  # type: ignore[no-untyped-call]
    cl.user_session.set("history", [])  # type: ignore[no-untyped-call]
    cl.user_session.set("document_ids", [])  # type: ignore[no-untyped-call]
    cl.user_session.set("document_full_contexts", [])  # type: ignore[no-untyped-call]

    # Rebuild LLM label map for settings widget
    settings = get_settings()
    google_label = f"Google Gemini ({settings.google_model})"
    anthropic_label = f"Anthropic Claude ({settings.anthropic_model})"
    ollama_label = f"Ollama ({settings.ollama_chat_model})"
    cl.user_session.set("_llm_label_map", {  # type: ignore[no-untyped-call]
        google_label: "google",
        anthropic_label: "anthropic",
        ollama_label: "ollama",
    })

    logger.info("Resumed thread %s for user=%s profile=%s", thread.get("id"), user_id, profile_name)


async def _init_session_common() -> tuple[str, str, str, str]:
    """Set up user ID and LLM label strings shared by both modes.

    Returns:
        Tuple of (user_id, google_label, anthropic_label, ollama_label).
    """
    user = cl.user_session.get("user")  # type: ignore[no-untyped-call]
    user_id = user.identifier if user else "anonymous"
    cl.user_session.set("user_id", user_id)  # type: ignore[no-untyped-call]

    settings = get_settings()
    google_label = f"Google Gemini ({settings.google_model})"
    anthropic_label = f"Anthropic Claude ({settings.anthropic_model})"
    ollama_label = f"Ollama ({settings.ollama_chat_model})"

    cl.user_session.set("_llm_label_map", {  # type: ignore[no-untyped-call]
        google_label: "google",
        anthropic_label: "anthropic",
        ollama_label: "ollama",
    })

    return user_id, google_label, anthropic_label, ollama_label


_EXECUTION_COUNT_VALUES = ["2", "3", "4", "5"]


async def _send_settings_widget(
    label: str, values: list[str], initial: str, description: str,
    *, include_execution_count: bool = False,
) -> None:
    """Send a ChatSettings widget, swallowing errors gracefully."""
    try:
        widgets = [
            Select(id="llm_provider", label=label, values=values,
                   initial_value=initial, description=description),
        ]
        if include_execution_count:
            widgets.append(
                Select(
                    id="execution_count",
                    label="Execution Count",
                    values=_EXECUTION_COUNT_VALUES,
                    initial_value="2",
                    description="Number of times to execute each prompt for reliability (2-5)",
                ),
            )
        await cl.ChatSettings(widgets).send()  # type: ignore[no-untyped-call]
    except Exception:
        logger.debug("Could not send ChatSettings widget", exc_info=True)


async def _init_chat_mode(profile_name: str) -> None:
    """Set up session for direct chat mode (no evaluation pipeline)."""
    cl.user_session.set("profile_mode", "chat")  # type: ignore[no-untyped-call]
    cl.user_session.set("chat_provider", "google")  # type: ignore[no-untyped-call]
    cl.user_session.set("chat_history", [])  # type: ignore[no-untyped-call]

    _, google_label, anthropic_label, ollama_label = await _init_session_common()

    await _send_settings_widget(
        "Chat LLM Provider",
        [google_label, anthropic_label, ollama_label],
        google_label,
        "Select which LLM to chat with",
    )

    await cl.Message(  # type: ignore[no-untyped-call]
        content=(
            f"# {profile_name}\n\n"
            "You are chatting directly with **Google Gemini** (default). "
            "Switch to Anthropic Claude or Ollama using the **settings widget** above.\n\n"
            "This is a free-form conversation — no prompt evaluation.\n\n"
            "The model's **thinking/reasoning** process will be displayed in a collapsible "
            "section above each response when available.\n\n"
            f"**Chat LLM:** {google_label} (change in settings)\n\n"
            "*Type your message below to start chatting.*"
        ),
    ).send()


async def _init_evaluator_mode(profile_name: str) -> None:
    """Set up session for the T.C.R.E.I. evaluation pipeline."""
    cl.user_session.set("profile_mode", "evaluator")  # type: ignore[no-untyped-call]
    task_type = _PROFILE_TO_TASK_TYPE.get(profile_name, TaskType.GENERAL)
    cl.user_session.set("task_type", task_type)  # type: ignore[no-untyped-call]
    cl.user_session.set("llm_provider", "google")  # type: ignore[no-untyped-call]
    cl.user_session.set("execution_count", 2)  # type: ignore[no-untyped-call]

    _, google_label, anthropic_label, ollama_label = await _init_session_common()

    await _send_settings_widget(
        "LLM Evaluator",
        [google_label, anthropic_label, ollama_label],
        google_label,
        "Select which LLM provider to use for evaluation",
        include_execution_count=True,
    )

    mode_detail = _WELCOME_MESSAGES.get(task_type, _DEFAULT_WELCOME)
    example = get_example_for_task_type(task_type)
    example_section = format_example_markdown(example)

    await cl.Message(  # type: ignore[no-untyped-call]
        content=(
            "# Professional Prompt Shaper\n\n"
            "Welcome to **Professional Prompt Shaper** \u2014 your AI-powered prompt quality assurance platform.\n\n"
            "I evaluate prompts against the **T.C.R.E.I.** framework "
            "(Task, Context, References, Evaluate, Iterate), scoring both **structural integrity** "
            "and **output quality** in a single pass.\n\n"
            "### How it works\n"
            "1. **Paste any prompt** below\n"
            "2. The evaluator runs a full professional audit \u2014 structure analysis + output quality evaluation\n"
            "3. Receive a detailed **audit report** with scores, findings, and an optimized prompt\n\n"
            f"{mode_detail}\n\n"
            f"**LLM Evaluator:** {google_label} (change in settings)\n\n"
            "---\n\n"
            f"### Example Prompt\n\n{example_section}\n\n"
            "---\n"
            "*Switch between profiles using the selector in the header above. "
            "Available: General Task, Email Creation, Summarization, Coding Task, "
            "Exam Interview Agent, LinkedIn Professional Post. Paste your prompt below to begin.*"
        ),
    ).send()


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize the chat session — delegates to mode-specific helpers."""
    cl.user_session.set("mode", EvalMode.PROMPT)  # type: ignore[no-untyped-call]
    cl.user_session.set("history", [])  # type: ignore[no-untyped-call]
    cl.user_session.set("document_ids", [])  # type: ignore[no-untyped-call]
    cl.user_session.set("document_full_contexts", [])  # type: ignore[no-untyped-call]

    profile_name: str = cl.user_session.get("chat_profile", "General Task Prompts")  # type: ignore[no-untyped-call]

    if profile_name == _CHAT_PROFILE_NAME:
        await _init_chat_mode(profile_name)
    else:
        await _init_evaluator_mode(profile_name)

    counter = increment_chat_counter()
    now = datetime.now()
    thread_name = f"Chat {counter} \u00b7 {now.strftime('%b %d, %I:%M %p')}"
    await _set_thread_name(thread_name)


@cl.on_settings_update  # type: ignore[misc]
async def on_settings_update(settings: dict) -> None:
    """Handle LLM provider and execution count changes from the header widget."""
    label = settings.get("llm_provider", "")
    label_map: dict = cl.user_session.get("_llm_label_map", {})  # type: ignore[no-untyped-call]
    provider = label_map.get(label, "google")

    profile_mode: str = cl.user_session.get("profile_mode", "evaluator")  # type: ignore[no-untyped-call]
    if profile_mode == "chat":
        cl.user_session.set("chat_provider", provider)  # type: ignore[no-untyped-call]
    else:
        cl.user_session.set("llm_provider", provider)  # type: ignore[no-untyped-call]

    # Handle execution count selection (evaluator mode only)
    exec_count_str = settings.get("execution_count", "")
    if exec_count_str and profile_mode != "chat":
        try:
            exec_count = int(exec_count_str)
            cl.user_session.set("execution_count", exec_count)  # type: ignore[no-untyped-call]
        except ValueError:
            pass

    audio_note = ""
    if provider != "google":
        audio_note = "\n\n*Audio recording is disabled — voice input requires Google Gemini.*"

    parts = [f"LLM provider switched to **{label}**."]
    if exec_count_str and profile_mode != "chat":
        parts.append(f"Execution count: **{exec_count_str}x**.")
    parts.append("Strategy: **Enhanced (CoT+ToT+Meta)** (always active).")
    parts.append(audio_note)

    await cl.Message(  # type: ignore[no-untyped-call]
        content=" ".join(parts)
    ).send()


# ===== Audio Handlers (speech-to-text via Gemini) ============================

@cl.on_audio_start  # type: ignore[misc]
async def on_audio_start() -> bool:
    """Accept an incoming audio stream if Google Gemini is the active provider.

    Audio transcription requires Google Gemini (the only provider with audio
    input support). When another provider is selected the recording is
    rejected and the user is informed.
    """
    profile_mode: str = cl.user_session.get("profile_mode", "evaluator")  # type: ignore[no-untyped-call]
    provider: str = (
        cl.user_session.get("chat_provider", "google")  # type: ignore[no-untyped-call]
        if profile_mode == "chat"
        else cl.user_session.get("llm_provider", "google")  # type: ignore[no-untyped-call]
    )

    if provider != "google":
        await cl.Message(  # type: ignore[no-untyped-call]
            content="**Audio recording is only available with Google Gemini.** "
            "Please switch your LLM provider to Google Gemini to use voice input.",
        ).send()
        return False

    cl.user_session.set("audio_chunks", [])  # type: ignore[no-untyped-call]
    cl.user_session.set("audio_mime", "audio/webm")  # type: ignore[no-untyped-call]
    return True


@cl.on_audio_chunk  # type: ignore[misc]
async def on_audio_chunk(chunk: cl.InputAudioChunk) -> None:  # type: ignore[name-defined]
    """Accumulate raw audio data as it streams from the browser."""
    if chunk.isStart:
        cl.user_session.set("audio_mime", chunk.mimeType)  # type: ignore[no-untyped-call]
    audio_chunks: list[bytes] = cl.user_session.get("audio_chunks", [])  # type: ignore[no-untyped-call]
    audio_chunks.append(chunk.data)
    cl.user_session.set("audio_chunks", audio_chunks)  # type: ignore[no-untyped-call]


@cl.on_audio_end  # type: ignore[misc]
async def on_audio_end() -> None:
    """Transcribe the recorded audio via Gemini, then route the text.

    Concatenates the buffered chunks, delegates PCM-to-WAV conversion and
    Gemini transcription to ``transcribe_audio()``, then feeds the resulting
    text into the chat or evaluation handler.
    """
    audio_chunks: list[bytes] = cl.user_session.get("audio_chunks", [])  # type: ignore[no-untyped-call]
    if not audio_chunks:
        await cl.Message(content="No audio data received.").send()  # type: ignore[no-untyped-call]
        return

    audio_data = b"".join(audio_chunks)
    mime_type: str = cl.user_session.get("audio_mime", "audio/webm")  # type: ignore[no-untyped-call]
    cl.user_session.set("audio_chunks", [])  # type: ignore[no-untyped-call]

    try:
        transcription = transcribe_audio(audio_data, mime_type)
    except Exception as e:
        logger.exception("Audio transcription failed: %s", e)
        await cl.Message(  # type: ignore[no-untyped-call]
            content=f"Audio transcription failed: {e}"
        ).send()
        return

    if not transcription:
        await cl.Message(content="Could not transcribe the audio.").send()  # type: ignore[no-untyped-call]
        return

    # Show what was transcribed (audio always uses Gemini regardless of selected provider)
    await cl.Message(content=f"**Transcribed (via Gemini):** {transcription}").send()  # type: ignore[no-untyped-call]

    # Route transcription through the existing pipeline
    profile_mode: str = cl.user_session.get("profile_mode", "evaluator")  # type: ignore[no-untyped-call]
    if profile_mode == "chat":
        await _handle_chat_message(transcription)
    else:
        mode: EvalMode = cl.user_session.get("mode", EvalMode.PROMPT)  # type: ignore[no-untyped-call]
        await _run_evaluation(transcription, mode)


async def _process_document_attachments(elements: list[Any]) -> str:
    """Process document attachments (PDF, DOCX, etc.) and return status text.

    Runs the document processing pipeline for each document file,
    stores document IDs in the user session, and caches the full document
    content (raw text + entities) so the LLM has complete information on
    the first query without losing any details.

    Args:
        elements: List of Chainlit element objects from the message.

    Returns:
        Status text to display to the user (processing summaries).
    """

    from src.db import get_session_factory
    from src.documents.processor import process_document

    text_prefix, image_blocks, document_paths = _process_attachments(list(elements))

    status_parts: list[str] = []
    if text_prefix:
        status_parts.append(text_prefix)

    if document_paths:
        user_id: str = cl.user_session.get("user_id", "anonymous")  # type: ignore[no-untyped-call]
        thread_id: str | None = getattr(cl.context.session, "thread_id", None)
        session_id: str = cl.user_session.get("id", "default")  # type: ignore[no-untyped-call]
        doc_ids: list[str] = cl.user_session.get("document_ids", [])  # type: ignore[no-untyped-call]
        doc_full_contexts: list[str] = cl.user_session.get("document_full_contexts", [])  # type: ignore[no-untyped-call]

        factory = get_session_factory()
        async with factory() as session:
            for doc_path, original_filename in document_paths:
                try:
                    result = await process_document(
                        session,
                        doc_path,
                        filename=original_filename,
                        user_id=user_id,
                        thread_id=thread_id,
                        session_id=session_id,
                    )
                    await session.commit()
                    doc_ids.append(str(result.document_id))
                    status_parts.append(result.display_summary)

                    # Cache full document content for the LLM
                    doc_full_contexts.append(
                        _build_full_document_context(result)
                    )
                except Exception as exc:
                    await session.rollback()
                    logger.warning("Document processing failed for %s: %s", original_filename, exc)
                    status_parts.append(f"*Failed to process `{original_filename}`: {exc}*")

        cl.user_session.set("document_ids", doc_ids)  # type: ignore[no-untyped-call]
        cl.user_session.set("document_full_contexts", doc_full_contexts)  # type: ignore[no-untyped-call]

        if any(doc_ids):
            doc_msg = "\n".join(status_parts[-len(document_paths):])
            await cl.Message(content=doc_msg).send()  # type: ignore[no-untyped-call]

    return text_prefix, image_blocks  # type: ignore[return-value]


def _build_full_document_context(result: Any) -> str:
    """Build a comprehensive document context string with ALL content.

    Includes the full raw text, extracted entities, and metadata so
    the LLM has complete information without losing any details.

    Args:
        result: ProcessingResult from the document processor.

    Returns:
        Formatted document context string.
    """
    parts: list[str] = []

    # Document header with metadata
    parts.append(f"## Document: {result.filename}")
    info: list[str] = [f"Type: {result.file_type.upper()}"]
    if result.page_count:
        info.append(f"Pages: {result.page_count}")
    if result.word_count:
        info.append(f"Words: {result.word_count:,}")
    parts.append(" | ".join(info))

    # Extracted entities
    if result.extractions:
        entity_lines: list[str] = []
        for entity in result.extractions:
            entity_lines.append(f"- {entity.entity_type}: {entity.value}")
        if entity_lines:
            parts.append("**Key entities extracted:**\n" + "\n".join(entity_lines))

    # Full document text — no truncation, no summarization
    parts.append("**Full document content:**")
    parts.append(result.raw_text)

    return "\n\n".join(parts)


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle incoming user messages — routes to chat or evaluation."""
    user_input = message.content.strip()
    if not user_input:
        return

    # Route based on profile mode
    profile_mode: str = cl.user_session.get("profile_mode", "evaluator")  # type: ignore[no-untyped-call]
    if profile_mode == "chat":
        # Process file attachments if present
        text_prefix = ""
        image_blocks: list[dict[str, Any]] | None = None
        if message.elements:
            text_prefix, image_blocks, document_paths = _process_attachments(list(message.elements))
            if not image_blocks:
                image_blocks = None

            # Process document attachments
            if document_paths:
                await _process_document_attachments(message.elements)

                # Use full document content (just uploaded)
                doc_full_contexts: list[str] = cl.user_session.get("document_full_contexts", [])  # type: ignore[no-untyped-call]
                if doc_full_contexts:
                    full_context = "\n\n---\n\n".join(doc_full_contexts)
                    text_prefix = f"{text_prefix}\n\n{full_context}".strip()

        # For follow-up messages (no new upload), use RAG to find relevant chunks
        if not text_prefix:
            doc_ids_in_session: list[str] = cl.user_session.get("document_ids", [])  # type: ignore[no-untyped-call]
            if doc_ids_in_session:
                doc_context = await _get_document_context_for_chat(user_input)
                if doc_context:
                    text_prefix = f"**Document context (from uploaded documents):**\n{doc_context}"

        augmented_input = f"{text_prefix}\n{user_input}".strip() if text_prefix else user_input
        await _handle_chat_message(augmented_input, image_blocks=image_blocks)
        return

    # Mode switch commands
    if "system prompt mode" in user_input.lower():
        cl.user_session.set("mode", EvalMode.SYSTEM_PROMPT)  # type: ignore[no-untyped-call]
        await cl.Message(  # type: ignore[no-untyped-call]
            content="Switched to **System Prompt Evaluation** mode. Paste your system prompt.",
        ).send()
        return

    if "prompt mode" in user_input.lower() and "system" not in user_input.lower():
        cl.user_session.set("mode", EvalMode.PROMPT)  # type: ignore[no-untyped-call]
        await cl.Message(  # type: ignore[no-untyped-call]
            content="Switched to **Prompt Evaluation** mode. Paste a prompt.",
        ).send()
        return

    # Process document attachments in evaluation mode too
    if message.elements:
        await _process_document_attachments(message.elements)

    mode: EvalMode = cl.user_session.get("mode", EvalMode.PROMPT)  # type: ignore[no-untyped-call]

    # Auto-detect system prompt markers
    system_signals = ["system prompt", "system message", "system instruction"]
    if any(s in user_input.lower() for s in system_signals):
        mode = EvalMode.SYSTEM_PROMPT
        cl.user_session.set("mode", mode)  # type: ignore[no-untyped-call]

    await _run_evaluation(user_input, mode)


async def _get_document_context_for_chat(query: str) -> str:
    """Retrieve document context for chat mode follow-up queries.

    Uses a two-tier strategy:
    1. First tries the Stuff strategy via RAG retriever (returns ALL chunks
       for small documents, ensuring zero information loss).
    2. For large documents, falls back to similarity-based retrieval
       (top-K most relevant chunks).

    Both strategies include document metadata and extracted entities.

    Args:
        query: The user's message to find relevant document chunks for.

    Returns:
        Formatted document context string, or empty string.
    """
    from src.db import get_session_factory
    from src.documents.retriever import retrieve_document_context

    doc_ids: list[str] = cl.user_session.get("document_ids", [])  # type: ignore[no-untyped-call]
    if not doc_ids:
        return ""

    user_id: str = cl.user_session.get("user_id", "anonymous")  # type: ignore[no-untyped-call]
    thread_id: str | None = getattr(cl.context.session, "thread_id", None)

    try:
        factory = get_session_factory()
        async with factory() as session:
            return await retrieve_document_context(
                session,
                query=query,
                user_id=user_id,
                thread_id=thread_id,
                document_ids=doc_ids,
            )
    except Exception as exc:
        logger.warning("Document context retrieval failed: %s", exc)
        return ""
