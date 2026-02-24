"""Pydantic models for document processing pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata extracted from a loaded document."""

    filename: str
    file_type: str
    file_size_bytes: int
    page_count: int | None = None
    word_count: int | None = None
    title: str | None = None
    author: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """A single chunk of a processed document."""

    chunk_index: int
    content: str
    page_number: int | None = None
    section_title: str | None = None
    char_offset: int = 0
    token_estimate: int = 0


class ExtractionEntity(BaseModel):
    """A structured entity extracted from document text via LangExtract."""

    entity_type: str
    value: str
    confidence: float = 1.0
    metadata: dict[str, str] = Field(default_factory=dict)


class ProcessingResult(BaseModel):
    """Complete result from the document processing pipeline."""

    document_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    filename: str
    file_type: str
    file_size_bytes: int
    page_count: int | None = None
    word_count: int | None = None
    raw_text: str
    summary: str
    extractions: list[ExtractionEntity] = Field(default_factory=list)
    chunks: list[DocumentChunk] = Field(default_factory=list)
    chunk_count: int = 0
    processing_time_seconds: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def display_summary(self) -> str:
        """Human-readable processing summary for Chainlit display."""
        parts = [f"Processed '{self.filename}'"]
        if self.page_count:
            parts.append(f"{self.page_count:,} pages")
        if self.word_count:
            parts.append(f"{self.word_count:,} words")
        parts.append(f"{self.chunk_count:,} chunks stored")
        return ": ".join([parts[0], ", ".join(parts[1:])])
