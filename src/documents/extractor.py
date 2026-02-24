"""Document extractor — structured entity extraction from document text via MapReduce."""

from __future__ import annotations

import asyncio
import json
import logging

from src.config import get_settings
from src.documents.models import ExtractionEntity

logger = logging.getLogger(__name__)

# Maximum characters per extraction window
_WINDOW_SIZE = 5000
_WINDOW_OVERLAP = 500


async def extract_entities(raw_text: str) -> list[ExtractionEntity]:
    """Extract structured entities from document text using MapReduce.

    For documents that exceed a single extraction window, splits the text
    into overlapping windows, extracts entities from each window in parallel
    (Map phase), then merges and deduplicates results (Reduce phase).

    This ensures no information is lost — the entire document is processed.

    Args:
        raw_text: The raw document text to extract entities from.

    Returns:
        List of ExtractionEntity objects. Returns empty list on failure.
    """
    settings = get_settings()

    if not settings.doc_enable_extraction:
        logger.debug("Entity extraction disabled via settings")
        return []

    if not raw_text.strip():
        return []

    # Split document into overlapping windows for MapReduce
    windows = _split_into_windows(raw_text, _WINDOW_SIZE, _WINDOW_OVERLAP)
    logger.info(
        "Extracting entities via MapReduce: %d windows from %d chars",
        len(windows),
        len(raw_text),
    )

    # MAP phase: extract entities from each window in parallel
    tasks = [_extract_from_window(window, idx, len(windows)) for idx, window in enumerate(windows)]
    window_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect all extracted entities
    all_entities: list[ExtractionEntity] = []
    for i, result in enumerate(window_results):
        if isinstance(result, BaseException):
            logger.warning("Window %d extraction failed: %s", i, result)
            continue
        all_entities.extend(result)

    # REDUCE phase: deduplicate entities
    merged = _deduplicate_entities(all_entities)

    logger.info(
        "MapReduce extraction complete: %d raw entities -> %d deduplicated",
        len(all_entities),
        len(merged),
    )
    return merged


def _split_into_windows(text: str, window_size: int, overlap: int) -> list[str]:
    """Split text into overlapping windows for parallel processing.

    Args:
        text: Full document text.
        window_size: Maximum characters per window.
        overlap: Character overlap between adjacent windows.

    Returns:
        List of text windows.
    """
    if len(text) <= window_size:
        return [text]

    windows: list[str] = []
    start = 0
    while start < len(text):
        end = start + window_size
        windows.append(text[start:end])
        start += window_size - overlap
        if start >= len(text):
            break

    return windows


async def _extract_from_window(text: str, window_idx: int, total_windows: int) -> list[ExtractionEntity]:
    """Extract entities from a single text window.

    Args:
        text: The text window to extract from.
        window_idx: Index of this window (for logging).
        total_windows: Total number of windows (for logging).

    Returns:
        List of extracted entities from this window.
    """
    try:
        from langchain_core.messages import SystemMessage
        from langchain_core.prompts import ChatPromptTemplate

        from src.utils.llm_factory import get_llm

        llm = get_llm()

        window_context = ""
        if total_windows > 1:
            window_context = f" This is section {window_idx + 1} of {total_windows} from a larger document."

        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=(
                        "Extract key entities from this document text. Return a JSON array of objects, "
                        "each with 'entity_type' (e.g., 'person', 'organization', 'date', 'topic', "
                        "'location', 'product', 'metric', 'skill', 'technology', 'role', 'education'), "
                        "'value' (the entity text), and "
                        "'confidence' (0.0 to 1.0). Extract ALL clearly identifiable entities — "
                        "do not skip any important information. "
                        f"Return at most 30 entities per section.{window_context} "
                        "Return ONLY the JSON array, no other text."
                    )
                ),
                ("human", "Extract entities from:\n\n{text}"),
            ]
        )

        chain = prompt | llm
        response = await chain.ainvoke({"text": text})

        # Parse the response
        content = response.content if hasattr(response, "content") else str(response)
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else getattr(block, "text", "") for block in content
            )

        # Try to extract JSON from response
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        entities_data = json.loads(content)

        entities: list[ExtractionEntity] = []
        for item in entities_data:
            if isinstance(item, dict) and "entity_type" in item and "value" in item:
                entities.append(
                    ExtractionEntity(
                        entity_type=item["entity_type"],
                        value=item["value"],
                        confidence=float(item.get("confidence", 1.0)),
                    )
                )

        logger.debug(
            "Window %d/%d: extracted %d entities",
            window_idx + 1,
            total_windows,
            len(entities),
        )
        return entities

    except Exception as exc:
        logger.warning("Entity extraction failed for window %d: %s", window_idx, exc)
        return []


def _deduplicate_entities(entities: list[ExtractionEntity]) -> list[ExtractionEntity]:
    """Deduplicate entities by (type, normalized_value), keeping highest confidence.

    Args:
        entities: All extracted entities from all windows.

    Returns:
        Deduplicated list of entities sorted by confidence descending.
    """
    seen: dict[tuple[str, str], ExtractionEntity] = {}

    for entity in entities:
        key = (entity.entity_type.lower().strip(), entity.value.lower().strip())
        existing = seen.get(key)
        if existing is None or entity.confidence > existing.confidence:
            seen[key] = entity

    # Sort by confidence descending
    return sorted(seen.values(), key=lambda e: e.confidence, reverse=True)
