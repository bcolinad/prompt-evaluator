"""Document vectorizer — embed chunks and store in pgvector."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.db.models import DocumentChunkRecord
from src.embeddings.service import generate_embedding

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.documents.models import DocumentChunk

logger = logging.getLogger(__name__)


async def vectorize_and_store(
    session: AsyncSession,
    document_id: uuid.UUID,
    chunks: list[DocumentChunk],
    user_id: str | None = None,
    thread_id: str | None = None,
) -> list[DocumentChunkRecord]:
    """Vectorize document chunks and store them in the database.

    Generates embeddings for each chunk via Ollama and persists them
    as DocumentChunkRecord rows with pgvector embeddings.

    Args:
        session: Async database session.
        document_id: UUID of the parent Document record.
        chunks: List of DocumentChunk objects to vectorize.
        user_id: Optional user identifier for scoping.
        thread_id: Optional Chainlit thread ID for cleanup.

    Returns:
        List of created DocumentChunkRecord objects.
    """
    records: list[DocumentChunkRecord] = []

    for chunk in chunks:
        try:
            embedding = await generate_embedding(chunk.content)
        except Exception as exc:
            logger.warning(
                "Failed to generate embedding for chunk %d of document %s: %s",
                chunk.chunk_index,
                document_id,
                exc,
            )
            continue

        record = DocumentChunkRecord(
            document_id=document_id,
            user_id=user_id,
            thread_id=thread_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            page_number=chunk.page_number,
            section_title=chunk.section_title,
            char_offset=chunk.char_offset,
            token_estimate=chunk.token_estimate,
            embedding=embedding,
        )
        session.add(record)
        records.append(record)

    await session.flush()
    logger.info(
        "Vectorized and stored %d/%d chunks for document %s",
        len(records),
        len(chunks),
        document_id,
    )
    return records
