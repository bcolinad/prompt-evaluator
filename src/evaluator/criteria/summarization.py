"""Summarization-specific evaluation criteria."""

from __future__ import annotations

from src.evaluator.criteria.base import Criterion

SUMMARIZATION_TASK_CRITERIA = [
    Criterion(
        name="content_scope_specified",
        description="The prompt specifies WHICH content to summarize — a portion of a document, a specific sub-topic, or the entire source. Google best practice: 'Specify which content you want the gen AI tool to summarize, such as a portion of a document or a specific sub topic'",
        detection_hint="Look for: 'summarize the findings section', 'summarize pages 5-10', 'summarize the entire report', 'focus on the methodology', 'condense the key arguments', 'distill the conclusions'. Also: summarize, condense, abstract, distill, recap, shorten, boil down",
        weight=0.25,
    ),
    Criterion(
        name="format_and_tone_defined",
        description="The prompt specifies the desired format (bullet points, paragraph, table) AND the tone or reading level. Google best practice: 'Include the desired format of the summary, such as bullet points, as well as the length and tone of the summary you want'",
        detection_hint="Look for FORMAT: 'bullet points', 'numbered list', 'paragraph form', 'table', 'executive summary', 'abstract', 'TL;DR', 'key takeaways'. Look for TONE: 'formal', 'casual', 'technical', 'plain language', 'fit a 9th grade reading level', 'non-technical', 'professional'",
        weight=0.30,
    ),
    Criterion(
        name="output_length_specified",
        description="The prompt specifies the desired length of the summary: word count, sentence count, paragraph count, or relative reduction ratio",
        detection_hint="Look for: 'in 200 words', '3-5 sentences', 'one paragraph', 'reduce to 10%', 'half the length', 'under 500 words', 'keep it brief', 'comprehensive overview', specific counts",
        weight=0.25,
    ),
    Criterion(
        name="persona_or_reading_level",
        description="The prompt assigns a persona or target reading level for the output. Google best practice: 'Add a persona, such as asking for the output to fit a 9th grade reading level'",
        detection_hint="Look for: 'as an analyst', 'act as a technical writer', 'as a researcher', 'you are an executive assistant', 'from the perspective of a...', 'at a 9th grade reading level', 'for a non-expert', 'for a specialist'",
        weight=0.20,
    ),
]

SUMMARIZATION_CONTEXT_CRITERIA = [
    Criterion(
        name="source_document_described",
        description="The prompt describes the source document: its type, title, subject, length, or origin — giving the gen AI enough context to understand what it is processing",
        detection_hint="Look for: 'this research paper', 'the following article', 'a 50-page report', 'meeting transcript', 'legal document', 'email thread', 'PDF report', document titles, subject descriptions, page/word counts",
        weight=0.30,
    ),
    Criterion(
        name="audience_for_summary",
        description="The prompt specifies who will read the summary and their background or expertise level, so the gen AI can calibrate vocabulary, depth, and detail",
        detection_hint="Look for: 'for executives', 'for a non-technical audience', 'for the board', 'for students', 'for my manager', 'for a 9th grader', target reader descriptions",
        weight=0.25,
    ),
    Criterion(
        name="summary_purpose",
        description="The prompt explains what the summary is for or why it is being created. Google best practice: 'Add additional context about what the summary is for or why you're creating it. This helps a gen AI tool anchor its response to something tangible'",
        detection_hint="Look for: 'for a decision', 'as a briefing', 'for quick reference', 'literature review', 'to share with the team', 'to prepare for a meeting', 'to get the gist of', 'to extract insights from', 'so I can understand the key points'",
        weight=0.25,
    ),
    Criterion(
        name="domain_specificity",
        description="The prompt includes domain-specific context such as industry terms, specialized vocabulary, or field-specific requirements that anchor the summary to the right domain",
        detection_hint="Look for: industry jargon, technical terms, legal terminology, medical vocabulary, financial concepts, academic discipline references, field-specific abbreviations",
        weight=0.20,
    ),
]

SUMMARIZATION_REFERENCES_CRITERIA = [
    Criterion(
        name="source_material_provided",
        description="The prompt includes, attaches, or clearly references the source text that needs to be summarized. Without the source material, the gen AI cannot produce an accurate summary",
        detection_hint="Look for: pasted text, 'the following document', 'attached file', 'the text below', 'here is the article', quoted source material, large blocks of text to summarize",
        weight=0.45,
    ),
    Criterion(
        name="example_summary_with_source",
        description="The prompt includes an example summary paired with the document it summarizes, so the gen AI knows what approach to take. Google best practice: 'Consider adding both the summary and the document it's summarizing as a reference so the tool knows what approach to take'",
        detection_hint="Look for: 'here is an example summary', 'like this summary of...', 'in this style', sample output paired with its source, 'similar to how this was summarized', a reference summary alongside the original",
        weight=0.30,
    ),
    Criterion(
        name="key_sections_identified",
        description="The prompt identifies which parts of the source to focus on or prioritize in the summary, helping the gen AI allocate attention to the most important content",
        detection_hint="Look for: 'focus on the methodology', 'prioritize the findings', 'emphasize the conclusions', 'skip the introduction', 'concentrate on chapters 3-5', section references, topic priorities",
        weight=0.25,
    ),
]

SUMMARIZATION_CONSTRAINTS_CRITERIA = [
    Criterion(
        name="length_word_limits",
        description="The prompt specifies hard length constraints for the summary output. Google iterate guidance: adjust the length if the summary isn't working for you",
        detection_hint="Look for: 'maximum 300 words', 'no more than 5 bullet points', 'keep under one page', 'exactly 3 paragraphs', specific word/sentence limits, 'brief', 'concise'",
        weight=0.25,
    ),
    Criterion(
        name="inclusion_requirements",
        description="The prompt specifies key findings, statistics, names, or facts that must be included in the summary to ensure nothing critical is lost during condensation",
        detection_hint="Look for: 'must include the key findings', 'include all statistics', 'mention the authors', 'retain the main conclusions', 'preserve the numbers', required elements",
        weight=0.25,
    ),
    Criterion(
        name="hallucination_safeguards",
        description="The prompt includes instructions to prevent hallucinations and misinterpretations — critical for summarization of large inputs. Google best practice: 'Large amounts of text can increase the chance of misinterpretations, irrelevant chains of thought, or even hallucinations'",
        detection_hint="Look for: 'no added interpretation', 'faithful to the source', 'do not editorialize', 'stick to the facts', 'objective summary', 'no opinion', 'do not fabricate', 'only use information from the source', 'cross-reference with the original'",
        weight=0.25,
    ),
    Criterion(
        name="exclusion_constraints",
        description="The prompt specifies sections, details, or types of information to omit from the summary. Google iterate guidance: ask the tool to 'adjust specific details about the output that aren't working for you'",
        detection_hint="Look for: 'exclude the appendix', 'skip the bibliography', 'omit technical details', 'leave out examples', 'do not include anecdotes', 'avoid jargon', 'no references section'",
        weight=0.25,
    ),
]

SUMMARIZATION_CRITERIA = {
    "task": SUMMARIZATION_TASK_CRITERIA,
    "context": SUMMARIZATION_CONTEXT_CRITERIA,
    "references": SUMMARIZATION_REFERENCES_CRITERIA,
    "constraints": SUMMARIZATION_CONSTRAINTS_CRITERIA,
}
