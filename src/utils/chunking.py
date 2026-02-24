"""Adaptive chunking for long, multi-section prompts.

Detects section boundaries via markdown headers, XML tags, and paragraph
breaks, then splits prompts into semantically meaningful chunks. Provides
score aggregation for per-chunk analysis results.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ChunkType(str, Enum):
    """Semantic type of a prompt chunk."""

    TASK = "task"
    CONTEXT = "context"
    EXAMPLES = "examples"
    CONSTRAINTS = "constraints"
    INSTRUCTIONS = "instructions"
    GENERAL = "general"


@dataclass
class PromptChunk:
    """A single chunk of a segmented prompt."""

    content: str
    chunk_type: ChunkType
    index: int
    char_offset: int
    token_estimate: int


# ── Section detection patterns ───────────────────────

_SECTION_PATTERNS: list[tuple[re.Pattern, ChunkType]] = [
    # Markdown headers
    (re.compile(r"^#{1,3}\s+.*task", re.IGNORECASE | re.MULTILINE), ChunkType.TASK),
    (re.compile(r"^#{1,3}\s+.*context", re.IGNORECASE | re.MULTILINE), ChunkType.CONTEXT),
    (re.compile(r"^#{1,3}\s+.*example", re.IGNORECASE | re.MULTILINE), ChunkType.EXAMPLES),
    (re.compile(r"^#{1,3}\s+.*constraint", re.IGNORECASE | re.MULTILINE), ChunkType.CONSTRAINTS),
    (re.compile(r"^#{1,3}\s+.*instruction", re.IGNORECASE | re.MULTILINE), ChunkType.INSTRUCTIONS),
    (re.compile(r"^#{1,3}\s+.*requirement", re.IGNORECASE | re.MULTILINE), ChunkType.CONSTRAINTS),
    (re.compile(r"^#{1,3}\s+.*reference", re.IGNORECASE | re.MULTILINE), ChunkType.EXAMPLES),
    # Generic markdown header (catch-all)
    (re.compile(r"^#{1,3}\s+\S", re.MULTILINE), ChunkType.GENERAL),
    # XML-style tags
    (re.compile(r"<task>", re.IGNORECASE), ChunkType.TASK),
    (re.compile(r"<context>", re.IGNORECASE), ChunkType.CONTEXT),
    (re.compile(r"<example", re.IGNORECASE), ChunkType.EXAMPLES),
    (re.compile(r"<constraint", re.IGNORECASE), ChunkType.CONSTRAINTS),
    (re.compile(r"<instruction", re.IGNORECASE), ChunkType.INSTRUCTIONS),
    (re.compile(r"<reference", re.IGNORECASE), ChunkType.EXAMPLES),
]

_TOKEN_ESTIMATE_RATIO = 4  # ~4 chars per token


def _estimate_tokens(text: str) -> int:
    """Rough token count estimate (4 chars per token)."""
    return max(1, len(text) // _TOKEN_ESTIMATE_RATIO)


def should_chunk(text: str, threshold: int = 2000) -> bool:
    """Return True if the prompt is long enough to benefit from chunking.

    Args:
        text: The prompt text to evaluate.
        threshold: Token estimate threshold (default 2000).
    """
    return _estimate_tokens(text) >= threshold


def detect_sections(text: str) -> list[tuple[int, ChunkType]]:
    """Detect section boundaries and their types in the text.

    Returns a list of (char_offset, ChunkType) tuples, sorted by offset.
    """
    sections: list[tuple[int, ChunkType]] = []
    seen_offsets: set[int] = set()

    for pattern, chunk_type in _SECTION_PATTERNS:
        for match in pattern.finditer(text):
            offset = match.start()
            if offset not in seen_offsets:
                sections.append((offset, chunk_type))
                seen_offsets.add(offset)

    sections.sort(key=lambda x: x[0])
    return sections


def chunk_prompt(text: str) -> list[PromptChunk]:
    """Split a prompt into semantically meaningful chunks.

    Strategy:
    1. If sections detected (markdown headers / XML tags), split at section boundaries
    2. Otherwise, split on paragraph breaks (double newlines)
    3. Merge very small chunks with their neighbors

    Args:
        text: The full prompt text.

    Returns:
        A list of PromptChunk objects.
    """
    text = text.strip()
    if not text:
        return []

    sections = detect_sections(text)

    if sections:
        return _chunk_by_sections(text, sections)
    else:
        return _chunk_by_paragraphs(text)


def _chunk_by_sections(text: str, sections: list[tuple[int, ChunkType]]) -> list[PromptChunk]:
    """Split text at detected section boundaries."""
    chunks = []

    # If first section doesn't start at 0, add a preamble chunk
    if sections[0][0] > 0:
        preamble = text[:sections[0][0]].strip()
        if preamble:
            chunks.append(PromptChunk(
                content=preamble,
                chunk_type=ChunkType.GENERAL,
                index=0,
                char_offset=0,
                token_estimate=_estimate_tokens(preamble),
            ))

    for i, (offset, chunk_type) in enumerate(sections):
        # Content runs to the start of the next section, or end of text
        end = sections[i + 1][0] if i + 1 < len(sections) else len(text)
        content = text[offset:end].strip()

        if content:
            chunks.append(PromptChunk(
                content=content,
                chunk_type=chunk_type,
                index=len(chunks),
                char_offset=offset,
                token_estimate=_estimate_tokens(content),
            ))

    return _merge_small_chunks(chunks)


def _chunk_by_paragraphs(text: str) -> list[PromptChunk]:
    """Split text on double-newline paragraph breaks."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    offset = 0

    for para in paragraphs:
        content = para.strip()
        if content:
            chunks.append(PromptChunk(
                content=content,
                chunk_type=ChunkType.GENERAL,
                index=len(chunks),
                char_offset=offset,
                token_estimate=_estimate_tokens(content),
            ))
        offset += len(para) + 2  # +2 for the \n\n separator

    return _merge_small_chunks(chunks)


def _merge_small_chunks(chunks: list[PromptChunk], min_tokens: int = 50) -> list[PromptChunk]:
    """Merge chunks that are too small with the next chunk."""
    if len(chunks) <= 1:
        return chunks

    merged = []
    i = 0
    while i < len(chunks):
        current = chunks[i]

        # If current chunk is too small and there's a next chunk, merge
        if current.token_estimate < min_tokens and i + 1 < len(chunks):
            next_chunk = chunks[i + 1]
            combined_content = f"{current.content}\n\n{next_chunk.content}"
            merged.append(PromptChunk(
                content=combined_content,
                chunk_type=next_chunk.chunk_type,
                index=len(merged),
                char_offset=current.char_offset,
                token_estimate=_estimate_tokens(combined_content),
            ))
            i += 2
        else:
            merged.append(PromptChunk(
                content=current.content,
                chunk_type=current.chunk_type,
                index=len(merged),
                char_offset=current.char_offset,
                token_estimate=current.token_estimate,
            ))
            i += 1

    return merged


def aggregate_dimension_scores(
    chunk_scores: list[dict],
    chunk_tokens: list[int],
) -> dict:
    """Aggregate per-chunk dimension scores into a single result.

    Uses token-weighted averaging for scores and OR-merge for flags.

    Args:
        chunk_scores: List of analysis results (each with "dimensions" and "tcrei_flags").
        chunk_tokens: List of token estimates per chunk (for weighting).

    Returns:
        A single aggregated analysis result dict.
    """
    if not chunk_scores:
        from src.agent.nodes.analyzer import _empty_analysis
        return _empty_analysis()

    if len(chunk_scores) == 1:
        return chunk_scores[0]

    total_tokens = sum(chunk_tokens)
    if total_tokens == 0:
        total_tokens = len(chunk_tokens)  # avoid division by zero

    # Weighted average for dimension scores
    dim_names = ["task", "context", "references", "constraints"]
    aggregated_dimensions = []

    for dim_name in dim_names:
        weighted_score = 0.0
        all_sub_criteria = {}

        for i, result in enumerate(chunk_scores):
            weight = chunk_tokens[i] / total_tokens
            dims = result.get("dimensions", [])
            dim = next((d for d in dims if d.name == dim_name), None)
            if dim is None:
                continue

            weighted_score += dim.score * weight

            # Deduplicate sub-criteria by name, keeping the most detailed
            for sc in dim.sub_criteria:
                if sc.name not in all_sub_criteria or len(sc.detail) > len(all_sub_criteria[sc.name].detail):
                    all_sub_criteria[sc.name] = sc

        from src.evaluator import DimensionScore
        aggregated_dimensions.append(DimensionScore(
            name=dim_name,
            score=round(weighted_score),
            sub_criteria=list(all_sub_criteria.values()),
        ))

    # OR-merge for flags (if any chunk detects a flag, it's present)
    from src.evaluator import TCREIFlags
    merged_flags = TCREIFlags()
    for result in chunk_scores:
        flags = result.get("tcrei_flags")
        if flags:
            merged_flags.task = merged_flags.task or flags.task
            merged_flags.context = merged_flags.context or flags.context
            merged_flags.references = merged_flags.references or flags.references
            merged_flags.evaluate = merged_flags.evaluate or flags.evaluate
            merged_flags.iterate = merged_flags.iterate or flags.iterate

    return {"dimensions": aggregated_dimensions, "tcrei_flags": merged_flags}
