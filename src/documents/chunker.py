"""Document chunker — split document text into chunks for vectorization."""

from __future__ import annotations

import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import get_settings
from src.documents.models import DocumentChunk

logger = logging.getLogger(__name__)


def chunk_document(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[DocumentChunk]:
    """Split document text into chunks suitable for vectorization.

    Uses RecursiveCharacterTextSplitter with document-aware separators
    that respect page boundaries (form-feed), section headings, and
    paragraph structure.

    Args:
        text: The full document text to chunk.
        chunk_size: Override chunk size (defaults to settings.doc_chunk_size).
        chunk_overlap: Override overlap (defaults to settings.doc_chunk_overlap).

    Returns:
        List of DocumentChunk objects with text content and metadata.
    """
    settings = get_settings()
    chunk_size = chunk_size or settings.doc_chunk_size
    chunk_overlap = chunk_overlap or settings.doc_chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\f",  # Page breaks (PDF form-feed)
            "\n## ",  # H2 headings (markdown sections, slides, sheets)
            "\n### ",  # H3 headings
            "\n\n",  # Paragraph breaks
            "\n",  # Line breaks
            ". ",  # Sentence boundaries
            " ",  # Word boundaries (last resort)
        ],
        length_function=len,
    )

    lc_chunks = splitter.split_text(text)

    chunks: list[DocumentChunk] = []
    char_offset = 0

    for i, chunk_text in enumerate(lc_chunks):
        # Find actual position in original text
        offset = text.find(chunk_text, char_offset)
        if offset == -1:
            offset = char_offset

        # Estimate page number from position (using form-feed markers)
        page_number = _estimate_page_number(text, offset)

        # Extract section title if chunk starts with a heading
        section_title = _extract_section_title(chunk_text)

        chunk = DocumentChunk(
            chunk_index=i,
            content=chunk_text,
            page_number=page_number,
            section_title=section_title,
            char_offset=offset,
            token_estimate=len(chunk_text) // 4,
        )
        chunks.append(chunk)
        char_offset = offset + len(chunk_text) - chunk_overlap

    logger.info("Chunked document into %d chunks (size=%d, overlap=%d)", len(chunks), chunk_size, chunk_overlap)
    return chunks


def _estimate_page_number(text: str, offset: int) -> int | None:
    """Estimate page number based on page break markers.

    Looks for common page break patterns (form feed characters, or
    section markers like '## Slide N' / '## Sheet:').

    Args:
        text: Full document text.
        offset: Character offset of the chunk.

    Returns:
        Estimated page number, or None if not determinable.
    """
    prefix = text[:offset]
    # Count form feed characters (PDF page breaks)
    ff_count = prefix.count("\f")
    if ff_count > 0:
        return ff_count + 1

    # Count slide/sheet markers
    import re

    markers = re.findall(r"## (?:Slide|Sheet)", prefix)
    if markers:
        return len(markers)

    return None


def _extract_section_title(chunk_text: str) -> str | None:
    """Extract section title if the chunk starts with a markdown heading.

    Args:
        chunk_text: The chunk text to scan.

    Returns:
        Section title string, or None.
    """
    for line in chunk_text.split("\n", 3):
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()[:512]
    return None
