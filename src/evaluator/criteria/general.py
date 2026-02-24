"""General T.C.R.E.I. evaluation criteria (Task, Context, References, Constraints)."""

from __future__ import annotations

from src.evaluator.criteria.base import Criterion

# ── Task Dimension ────────────────────────────────────
TASK_CRITERIA = [
    Criterion(
        name="clear_action_verb",
        description="The prompt contains a clear, imperative action verb that specifies what to do",
        detection_hint="Look for verbs like: write, create, draft, list, summarize, analyze, generate, build, design, explain, compare, evaluate",
        weight=0.25,
    ),
    Criterion(
        name="specific_deliverable",
        description="The prompt specifies exactly what output is expected (not vague like 'something about X')",
        detection_hint="Check for specific nouns: article, report, list, table, email, script, summary, plan, guide, presentation",
        weight=0.30,
    ),
    Criterion(
        name="persona_defined",
        description="The prompt assigns a persona or expertise level to the AI",
        detection_hint="Look for patterns: 'You are a...', 'Act as a...', 'As a...', 'You're a...', 'From the perspective of...'",
        weight=0.25,
    ),
    Criterion(
        name="output_format_specified",
        description="The prompt specifies the desired output format",
        detection_hint="Look for: bullet list, numbered list, table, paragraph, JSON, markdown, email format, specific word/page count",
        weight=0.20,
    ),
]

# ── Context Dimension ─────────────────────────────────
CONTEXT_CRITERIA = [
    Criterion(
        name="background_provided",
        description="The prompt includes background information or situational context",
        detection_hint="Look for: reasons, motivations, project descriptions, 'because', 'the situation is', 'I'm working on'",
        weight=0.25,
    ),
    Criterion(
        name="audience_defined",
        description="The prompt specifies who the output is for",
        detection_hint="Look for: 'for beginners', 'aimed at executives', 'for my team', 'targeting developers', specific audience names",
        weight=0.25,
    ),
    Criterion(
        name="goals_stated",
        description="The prompt explains the purpose or goal of the output",
        detection_hint="Look for: 'the goal is', 'I want to achieve', 'this will be used for', 'to help with', objective statements",
        weight=0.25,
    ),
    Criterion(
        name="domain_specificity",
        description="The prompt includes domain-specific details that narrow the scope",
        detection_hint="Look for: industry terms, specific technologies, geographic scope, time periods, specialized vocabulary",
        weight=0.25,
    ),
]

# ── References Dimension ──────────────────────────────
REFERENCES_CRITERIA = [
    Criterion(
        name="examples_included",
        description="The prompt includes examples of expected output or input/output pairs",
        detection_hint="Look for: 'for example', 'like this', 'here's an example', sample text, quoted examples",
        weight=0.40,
    ),
    Criterion(
        name="structured_references",
        description="References are structured with XML tags, headings, or clear delimiters",
        detection_hint="Look for: XML tags (<example>), markdown headings, labeled sections, 'Reference 1:', numbered examples",
        weight=0.30,
    ),
    Criterion(
        name="reference_labeling",
        description="References are clearly introduced with transitional phrases",
        detection_hint="Look for: 'Refer to these materials', 'Use the following examples', 'Based on this', 'Reference the'",
        weight=0.30,
    ),
]

# ── Constraints Dimension ─────────────────────────────
CONSTRAINTS_CRITERIA = [
    Criterion(
        name="scope_boundaries",
        description="The prompt defines clear boundaries on what to include or focus on",
        detection_hint="Look for: 'only include', 'focus on', 'limited to', 'specific to', geographic/temporal/topical boundaries",
        weight=0.25,
    ),
    Criterion(
        name="format_constraints",
        description="The prompt specifies formatting restrictions beyond basic format",
        detection_hint="Look for: 'use headers', 'no jargon', 'plain language', 'technical writing style', tone requirements",
        weight=0.25,
    ),
    Criterion(
        name="length_limits",
        description="The prompt specifies length or size constraints",
        detection_hint="Look for: word count, page count, number of items, 'brief', 'concise', 'comprehensive', 'in X words'",
        weight=0.25,
    ),
    Criterion(
        name="exclusions_defined",
        description="The prompt explicitly states what to exclude or avoid",
        detection_hint="Look for: 'do not include', 'avoid', 'exclude', 'should not', 'don't mention', 'leave out'",
        weight=0.25,
    ),
]

ALL_CRITERIA = {
    "task": TASK_CRITERIA,
    "context": CONTEXT_CRITERIA,
    "references": REFERENCES_CRITERIA,
    "constraints": CONSTRAINTS_CRITERIA,
}
