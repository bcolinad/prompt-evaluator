"""Document processor — orchestrates the full document processing pipeline."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from src.config import get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Document
from src.documents.chunker import chunk_document
from src.documents.exceptions import DocumentProcessingError
from src.documents.extractor import extract_entities
from src.documents.loader import SUPPORTED_EXTENSIONS, load_document
from src.documents.models import ProcessingResult
from src.documents.vectorizer import vectorize_and_store

logger = logging.getLogger(__name__)


async def process_document(
    session: AsyncSession,
    file_path: Path,
    filename: str | None = None,
    user_id: str | None = None,
    thread_id: str | None = None,
    session_id: str | None = None,
) -> ProcessingResult:
    """Run the full document processing pipeline.

    Pipeline stages:
    1. Load document (file -> text) via LangChain loaders
    2. Extract structured entities via LLM (optional)
    3. Chunk document text for vectorization
    4. Vectorize chunks and store in pgvector
    5. Persist document metadata to database

    Args:
        session: Async database session.
        file_path: Path to the uploaded file on disk.
        filename: Original filename.
        user_id: Authenticated user identifier.
        thread_id: Chainlit thread ID.
        session_id: Chainlit session ID.

    Returns:
        ProcessingResult with document metadata and processing stats.

    Raises:
        DocumentProcessingError: If any stage fails critically.
    """
    start_time = time.monotonic()
    if filename is None:
        filename = file_path.name

    settings = get_settings()

    # Check file size
    try:
        file_size = file_path.stat().st_size
    except OSError as exc:
        raise DocumentProcessingError(
            f"Cannot access file: {exc}",
            filename=filename,
            stage="validation",
        ) from exc

    if file_size > settings.doc_max_file_size:
        max_mb = settings.doc_max_file_size // (1024 * 1024)
        raise DocumentProcessingError(
            f"File exceeds {max_mb}MB limit ({file_size / (1024 * 1024):.1f}MB)",
            filename=filename,
            stage="validation",
        )

    # Stage 1: Load document
    raw_text, metadata = await load_document(file_path, filename)

    if not raw_text.strip():
        raise DocumentProcessingError(
            "Document appears to be empty — no text could be extracted.",
            filename=filename,
            stage="loader",
        )

    # Stage 2: Extract entities (optional, non-fatal)
    extractions = await extract_entities(raw_text)

    # Stage 3: Chunk document
    chunks = chunk_document(raw_text)

    # Generate a brief summary
    summary = _generate_summary(raw_text, metadata.filename)

    # Stage 4: Persist document record
    doc_id = uuid.uuid4()
    doc_record = Document(
        id=doc_id,
        user_id=user_id,
        thread_id=thread_id,
        session_id=session_id,
        filename=metadata.filename,
        file_type=metadata.file_type,
        file_size_bytes=metadata.file_size_bytes,
        page_count=metadata.page_count,
        word_count=metadata.word_count,
        raw_text=raw_text,
        summary=summary,
        extractions=[e.model_dump() for e in extractions] if extractions else None,
        chunk_count=len(chunks),
        processing_time_seconds=time.monotonic() - start_time,
    )
    session.add(doc_record)
    await session.flush()

    # Stage 5: Vectorize and store chunks
    await vectorize_and_store(session, doc_id, chunks, user_id=user_id, thread_id=thread_id)

    processing_time = time.monotonic() - start_time

    result = ProcessingResult(
        document_id=doc_id,
        filename=metadata.filename,
        file_type=metadata.file_type,
        file_size_bytes=metadata.file_size_bytes,
        page_count=metadata.page_count,
        word_count=metadata.word_count,
        raw_text=raw_text,
        summary=summary,
        extractions=extractions,
        chunks=chunks,
        chunk_count=len(chunks),
        processing_time_seconds=processing_time,
    )

    logger.info(
        "Document processing complete: '%s' — %d chunks, %.1fs",
        filename,
        len(chunks),
        processing_time,
    )

    return result


def _generate_summary(raw_text: str, filename: str) -> str:
    """Generate a comprehensive summary of the document content.

    Includes basic stats and a longer preview to capture more context.

    Args:
        raw_text: Full document text.
        filename: Original filename.

    Returns:
        Summary string with document statistics and content preview.
    """
    word_count = len(raw_text.split())
    char_count = len(raw_text)

    # Use a generous preview (up to 2000 chars) to capture document structure
    preview = raw_text[:2000].strip()
    if char_count > 2000:
        preview += f"... [{char_count - 2000:,} more characters]"

    return f"Document '{filename}' ({word_count:,} words, {char_count:,} characters). Content preview:\n{preview}"


def is_supported_document(filename: str) -> bool:
    """Check if a filename has a supported document extension.

    Args:
        filename: The filename to check.

    Returns:
        True if the extension is supported for document processing.
    """
    suffix = Path(filename).suffix.lower()
    return suffix in SUPPORTED_EXTENSIONS
