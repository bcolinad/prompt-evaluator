"""Markdown formatter for example prompts with T.C.R.E.I. breakdowns.

Produces compact, pure Markdown output (no HTML) suitable for Chainlit's
message rendering with ``unsafe_allow_html = false``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.evaluator.example_prompts import ExamplePrompt

# Dimension prefix letters for display
_DIMENSION_PREFIX: dict[str, str] = {
    "Task": "T",
    "Context": "C",
    "References": "R",
    "Constraints": "E/I",
}


def format_example_markdown(example: ExamplePrompt) -> str:
    """Format an example prompt as compact Markdown with T.C.R.E.I. summary.

    Produces a short, readable output: title with score, the full prompt in a
    code block, and a one-line summary per dimension.

    Args:
        example: The example prompt to format.

    Returns:
        A compact Markdown string.
    """
    lines: list[str] = []

    # Header with score
    lines.append(
        f"**{example.title}** | "
        f"Estimated Score: **{example.estimated_score}/100**"
    )
    lines.append("")

    # Full prompt in code block
    lines.append("```")
    lines.append(example.full_prompt)
    lines.append("```")
    lines.append("")

    # Compact T.C.R.E.I. breakdown — one line per dimension
    for section in example.sections:
        prefix = _DIMENSION_PREFIX.get(section.dimension, "?")
        lines.append(f"- **[{prefix}] {section.dimension}**: {section.label}")

    lines.append("")
    lines.append("*Paste your own prompt below to see how it compares.*")

    return "\n".join(lines)
