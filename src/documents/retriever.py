"""Document retriever — RAG-based document chunk retrieval via pgvector.

Implements two retrieval strategies:
- **Stuff**: For small documents (<=50 chunks), retrieves ALL chunks and sends
  the complete content to the LLM. No information is lost.
- **MapReduce**: For large documents (>50 chunks), retrieves top-K relevant
  chunks via cosine similarity, then groups them by document and includes
  document-level metadata + entities for comprehensive context.

Both strategies include document metadata (filename, entities, summary) so the
LLM always has full awareness of what information the documents contain.
"""

from __future__ import annotations

import logging
import uuid as uuid_mod
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from src.config import get_settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Document, DocumentChunkRecord
from src.embeddings.service import generate_embedding

logger = logging.getLogger(__name__)

# Documents with this many chunks or fewer use the "stuff" strategy
# (all chunks returned in order, no information loss)
_STUFF_THRESHOLD = 50


async def retrieve_document_context(
    session: AsyncSession,
    query: str,
    user_id: str | None = None,
    thread_id: str | None = None,
    document_ids: list[str] | None = None,
    top_k: int | None = None,
) -> str:
    """Retrieve relevant document chunks for a query via cosine similarity.

    Automatically selects the best retrieval strategy:
    - **Stuff** (<=50 total chunks): Returns ALL chunks in document order.
      This ensures zero information loss for small-to-medium documents.
    - **Similarity** (>50 total chunks): Returns top-K most relevant chunks
      ranked by cosine similarity, with document metadata and entities.

    Both strategies include document-level metadata (filename, summary,
    extracted entities) so the LLM always has full context.

    Args:
        session: Async database session.
        query: The user query to find relevant chunks for.
        user_id: Optional user ID to scope results.
        thread_id: Optional thread ID to scope results.
        document_ids: Optional list of specific document IDs to search.
        top_k: Number of top chunks to return (defaults to settings).

    Returns:
        Formatted string of relevant document chunks, or empty string.
    """
    settings = get_settings()
    top_k = top_k or settings.doc_max_chunks_per_query

    try:
        query_embedding = await generate_embedding(query)
    except Exception as exc:
        logger.warning("Failed to generate query embedding for document retrieval: %s", exc)
        return ""

    # Build base WHERE filters
    where_filters = _build_where_filters(user_id, thread_id, document_ids)

    # Count total chunks to decide strategy
    total_chunk_count = await _count_chunks(session, where_filters)
    if total_chunk_count == 0:
        return ""

    # Strategy selection: Stuff vs Similarity-based retrieval
    if total_chunk_count <= _STUFF_THRESHOLD:
        strategy = "stuff"
        rows = await _retrieve_all_chunks_ordered(session, where_filters)
    else:
        strategy = "similarity"
        rows = await _retrieve_by_similarity(session, query_embedding, where_filters, top_k)

    if not rows:
        return ""

    # Fetch document-level metadata for each unique document
    doc_ids_in_results = list({row.document_id for row in rows})
    doc_metadata = await _fetch_document_metadata(session, doc_ids_in_results)

    # Build structured context
    context = _build_context(rows, doc_metadata, strategy, total_chunk_count)

    logger.info(
        "Retrieved %d/%d document chunks via %s strategy for query",
        len(rows),
        total_chunk_count,
        strategy,
    )
    return context


async def retrieve_full_document_text(
    session: AsyncSession,
    document_ids: list[str],
) -> str:
    """Retrieve the full raw text of documents directly from the database.

    This bypasses RAG entirely and returns the complete document content
    as stored in the documents table. Use this when you need 100% of the
    document content with zero information loss.

    Args:
        session: Async database session.
        document_ids: List of document ID strings.

    Returns:
        Full document text with metadata headers, or empty string.
    """
    parsed_uuids: list[uuid_mod.UUID] = []
    for did in document_ids:
        try:
            parsed_uuids.append(uuid_mod.UUID(did))
        except ValueError:
            continue

    if not parsed_uuids:
        return ""

    stmt = select(
        Document.id,
        Document.filename,
        Document.file_type,
        Document.page_count,
        Document.word_count,
        Document.raw_text,
        Document.extractions,
    ).where(Document.id.in_(parsed_uuids))

    try:
        result = await session.execute(stmt)
        rows = result.fetchall()
    except Exception as exc:
        logger.warning("Failed to retrieve full document text: %s", exc)
        return ""

    if not rows:
        return ""

    parts: list[str] = []
    for row in rows:
        doc_parts: list[str] = [f"## Document: {row.filename}"]

        info: list[str] = []
        if row.file_type:
            info.append(f"Type: {row.file_type.upper()}")
        if row.page_count:
            info.append(f"Pages: {row.page_count}")
        if row.word_count:
            info.append(f"Words: {row.word_count:,}")
        if info:
            doc_parts.append(" | ".join(info))

        if row.extractions and isinstance(row.extractions, list):
            entity_lines = [
                f"- {e['entity_type']}: {e['value']}"
                for e in row.extractions
                if isinstance(e, dict) and "entity_type" in e and "value" in e
            ]
            if entity_lines:
                doc_parts.append("**Key entities:**\n" + "\n".join(entity_lines))

        doc_parts.append("**Full document content:**")
        doc_parts.append(row.raw_text or "")
        parts.append("\n\n".join(doc_parts))

    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
#  Internal helpers
# ---------------------------------------------------------------------------


def _build_where_filters(
    user_id: str | None,
    thread_id: str | None,
    document_ids: list[str] | None,
) -> dict[str, Any]:
    """Build a dict of WHERE filter values for reuse across queries.

    Args:
        user_id: Optional user ID to scope results.
        thread_id: Optional thread ID to scope results.
        document_ids: Optional list of specific document ID strings.

    Returns:
        Dict with keys 'user_id', 'thread_id', 'parsed_uuids'.
    """
    parsed_uuids: list[uuid_mod.UUID] = []
    if document_ids:
        for did in document_ids:
            try:
                parsed_uuids.append(uuid_mod.UUID(did))
            except ValueError:
                continue

    return {
        "user_id": user_id if user_id and user_id != "anonymous" else None,
        "thread_id": thread_id,
        "parsed_uuids": parsed_uuids,
    }


def _apply_where_filters(stmt: Any, filters: dict[str, Any]) -> Any:
    """Apply WHERE filters to a SQLAlchemy select statement.

    Args:
        stmt: The base select statement.
        filters: Filter dict from _build_where_filters.

    Returns:
        The filtered select statement.
    """
    if filters["user_id"]:
        stmt = stmt.where(DocumentChunkRecord.user_id == filters["user_id"])
    if filters["thread_id"]:
        stmt = stmt.where(DocumentChunkRecord.thread_id == filters["thread_id"])
    if filters["parsed_uuids"]:
        stmt = stmt.where(DocumentChunkRecord.document_id.in_(filters["parsed_uuids"]))
    return stmt


async def _count_chunks(session: AsyncSession, filters: dict[str, Any]) -> int:
    """Count total chunks matching the scope filters.

    Args:
        session: Async database session.
        filters: Filter dict from _build_where_filters.

    Returns:
        Total number of matching chunks.
    """
    from sqlalchemy import func

    stmt = select(func.count(DocumentChunkRecord.id))
    stmt = _apply_where_filters(stmt, filters)

    try:
        result = await session.execute(stmt)
        return result.scalar() or 0
    except Exception:
        return 0


async def _retrieve_all_chunks_ordered(
    session: AsyncSession,
    filters: dict[str, Any],
) -> list[Any]:
    """Retrieve ALL chunks in document order (Stuff strategy).

    Used for small-to-medium documents where we can fit everything
    into the LLM context without losing any information.

    Args:
        session: Async database session.
        filters: Filter dict from _build_where_filters.

    Returns:
        All matching chunk rows ordered by document_id and chunk_index.
    """
    stmt = select(
        DocumentChunkRecord.content,
        DocumentChunkRecord.page_number,
        DocumentChunkRecord.section_title,
        DocumentChunkRecord.chunk_index,
        DocumentChunkRecord.document_id,
    ).order_by(
        DocumentChunkRecord.document_id,
        DocumentChunkRecord.chunk_index,
    )
    stmt = _apply_where_filters(stmt, filters)

    try:
        result = await session.execute(stmt)
        return list(result.fetchall())
    except Exception as exc:
        logger.warning("Stuff retrieval query failed: %s", exc)
        return []


async def _retrieve_by_similarity(
    session: AsyncSession,
    query_embedding: list[float],
    filters: dict[str, Any],
    top_k: int,
) -> list[Any]:
    """Retrieve top-K chunks ranked by cosine similarity.

    Used for large documents where we cannot fit all chunks.

    Args:
        session: Async database session.
        query_embedding: The query's embedding vector.
        filters: Filter dict from _build_where_filters.
        top_k: Maximum number of chunks to retrieve.

    Returns:
        Top-K most relevant chunk rows.
    """
    distance_col = DocumentChunkRecord.embedding.cosine_distance(query_embedding).label("distance")

    stmt = (
        select(
            DocumentChunkRecord.content,
            DocumentChunkRecord.page_number,
            DocumentChunkRecord.section_title,
            DocumentChunkRecord.chunk_index,
            DocumentChunkRecord.document_id,
            distance_col,
        )
        .order_by(DocumentChunkRecord.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )
    stmt = _apply_where_filters(stmt, filters)

    try:
        result = await session.execute(stmt)
        return list(result.fetchall())
    except Exception as exc:
        logger.warning("Similarity retrieval query failed: %s", exc)
        return []


async def _fetch_document_metadata(
    session: AsyncSession,
    doc_ids: list[Any],
) -> dict[Any, dict[str, Any]]:
    """Fetch document-level metadata (filename, summary, entities) for documents.

    Args:
        session: Async database session.
        doc_ids: List of document UUIDs.

    Returns:
        Dict mapping document_id to metadata dict.
    """
    if not doc_ids:
        return {}

    stmt = select(
        Document.id,
        Document.filename,
        Document.file_type,
        Document.page_count,
        Document.word_count,
        Document.summary,
        Document.extractions,
    ).where(Document.id.in_(doc_ids))

    try:
        result = await session.execute(stmt)
        rows = result.fetchall()
    except Exception as exc:
        logger.warning("Failed to fetch document metadata: %s", exc)
        return {}

    return {
        row.id: {
            "filename": row.filename,
            "file_type": row.file_type,
            "page_count": row.page_count,
            "word_count": row.word_count,
            "summary": row.summary,
            "extractions": row.extractions,
        }
        for row in rows
    }


def _build_context(
    rows: list[Any],
    doc_metadata: dict[Any, dict[str, Any]],
    strategy: str,
    total_chunk_count: int,
) -> str:
    """Build the final context string from retrieved chunks and metadata.

    Args:
        rows: Retrieved chunk rows.
        doc_metadata: Document metadata keyed by document_id.
        strategy: 'stuff' or 'similarity'.
        total_chunk_count: Total chunks available.

    Returns:
        Formatted context string for LLM consumption.
    """
    context_parts: list[str] = []

    # Add document headers with metadata and entities
    doc_ids_in_results = list({row.document_id for row in rows})
    for doc_id in doc_ids_in_results:
        meta = doc_metadata.get(doc_id)
        if meta:
            context_parts.append(_format_document_header(meta))

    # Strategy indicator
    if strategy == "stuff":
        context_parts.append(f"## Complete Document Content ({len(rows)}/{total_chunk_count} chunks — full document)")
    else:
        context_parts.append(f"## Most Relevant Passages ({len(rows)}/{total_chunk_count} chunks by relevance)")

    # Add chunks
    for row in rows:
        header_parts: list[str] = []
        if row.section_title:
            header_parts.append(row.section_title)
        if row.page_number:
            header_parts.append(f"Page {row.page_number}")
        header = f"[{' | '.join(header_parts)}] " if header_parts else ""
        context_parts.append(f"{header}{row.content}")

    return "\n\n---\n\n".join(context_parts)


def _format_document_header(meta: dict[str, Any]) -> str:
    """Format document-level metadata into a structured header for the LLM.

    Args:
        meta: Document metadata dict from _fetch_document_metadata.

    Returns:
        Formatted header string.
    """
    parts: list[str] = [f"## Document: {meta['filename']}"]

    info_parts: list[str] = []
    if meta.get("file_type"):
        info_parts.append(f"Type: {meta['file_type'].upper()}")
    if meta.get("page_count"):
        info_parts.append(f"Pages: {meta['page_count']}")
    if meta.get("word_count"):
        info_parts.append(f"Words: {meta['word_count']:,}")
    if info_parts:
        parts.append(" | ".join(info_parts))

    # Include extracted entities for quick reference
    extractions = meta.get("extractions")
    if extractions and isinstance(extractions, list):
        entity_lines: list[str] = []
        for entity in extractions:
            if isinstance(entity, dict) and "entity_type" in entity and "value" in entity:
                entity_lines.append(f"- {entity['entity_type']}: {entity['value']}")
        if entity_lines:
            parts.append("**Key entities:**\n" + "\n".join(entity_lines))

    return "\n".join(parts)
