# T.C.R.E.I. Prompting Framework — Reference Guide

## Overview

The T.C.R.E.I. framework (based on Google's prompting best practices) provides a structured approach to crafting effective prompts. Each dimension addresses a different aspect of prompt quality.

## Task

The Task dimension evaluates whether the prompt clearly specifies what the AI should do.

### What makes a strong Task:
- **Clear action verb**: The prompt begins with or contains an imperative verb (write, create, analyze, summarize, compare, generate, list, draft, design, evaluate)
- **Specific deliverable**: The prompt names the exact output expected (e.g., "a 500-word blog post", "a comparison table", "a bullet-point summary")
- **Persona or expertise**: The prompt assigns a role or perspective (e.g., "You are a senior data scientist", "Act as a technical writer")
- **Output format**: The prompt specifies how the output should be structured (JSON, markdown table, numbered list, paragraph, email format)

### Common Task weaknesses:
- Vague requests like "tell me about X" or "help with Y"
- No specified deliverable type
- Missing persona when domain expertise matters
- Ambiguous format expectations

### Task scoring guidance:
- 81-100: All four sub-criteria present and specific
- 61-80: Three sub-criteria present, minor gaps
- 41-60: Action verb present but deliverable or format vague
- 21-40: Only a vague request detected
- 0-20: No discernible task

## Context

The Context dimension evaluates whether the prompt provides sufficient background for the AI to produce relevant output.

### What makes strong Context:
- **Background information**: The prompt explains the situation, project, or problem being addressed
- **Target audience**: The prompt identifies who will read or use the output (beginners, executives, developers, patients)
- **Goals and purpose**: The prompt explains why the output is needed and what it will be used for
- **Domain specificity**: The prompt includes industry terms, geographic scope, time periods, or technical constraints

### Common Context weaknesses:
- No explanation of why the output is needed
- Missing audience specification leading to wrong tone/depth
- Generic requests without domain grounding
- No project or situational background

### Context scoring guidance:
- 81-100: Rich background, clear audience, stated goals, domain-specific
- 61-80: Three of four sub-criteria present
- 41-60: Some background but missing audience or goals
- 21-40: Minimal context provided
- 0-20: No context at all

## References

The References dimension evaluates whether the prompt includes examples, templates, or reference materials.

### What makes strong References:
- **Examples included**: The prompt contains input/output examples, sample text, or demonstrations of expected quality
- **Structured references**: Examples are organized with XML tags, markdown headings, or clear delimiters
- **Reference labeling**: References are introduced with phrases like "Refer to these materials", "Use the following examples", "Based on this template"

### Common References weaknesses:
- No examples of expected output
- Unstructured reference dumps without labels
- Missing few-shot examples for complex tasks
- No style or quality references

### References scoring guidance:
- 81-100: Multiple labeled, structured examples with clear intent
- 61-80: At least one clear example with some structure
- 41-60: Vague references or unstructured examples
- 21-40: Passing mention of references without content
- 0-20: No references at all

## Constraints (formerly Evaluate)

The Constraints dimension evaluates whether the prompt sets clear boundaries on the output.

### What makes strong Constraints:
- **Scope boundaries**: The prompt defines what to include and exclude (topics, time periods, geographic scope)
- **Format constraints**: Beyond basic format, specific style requirements (tone, reading level, technical depth)
- **Length limits**: Word count, page count, number of items, or qualitative limits (brief, comprehensive)
- **Exclusions defined**: Explicit statements about what to avoid or leave out

### Common Constraints weaknesses:
- No limits on scope leading to unfocused output
- Missing length guidance
- No exclusions allowing irrelevant content
- Tone or style not specified

### Constraints scoring guidance:
- 81-100: Clear boundaries, length limits, exclusions, and style constraints
- 61-80: Three of four sub-criteria present
- 41-60: Some constraints but major gaps
- 21-40: Only vague limitations
- 0-20: No constraints at all

## LinkedIn Professional Post — Domain-Specific Guidance

When evaluating prompts for LinkedIn professional posts, the T.C.R.E.I. dimensions are adapted:

### Task (LinkedIn)
- **Post objective**: Thought leadership, industry insight, personal story, how-to, announcement, or commentary
- **Writing voice**: Authoritative, conversational, storytelling, data-driven, provocative, or inspirational
- **Content format**: Text post, carousel, poll, article, listicle, or story-based post
- **Call to action**: Comment, share, visit link, engage with question, or tag someone

### Context (LinkedIn)
- **Target audience**: Industry, role, seniority level, or professional community (e.g., "HR leaders and CHROs")
- **Author identity**: Professional brand, expertise area, credibility basis (e.g., "VP of Talent Acquisition with 15 years experience")
- **Industry/topic context**: Trends, news hooks, seasonal relevance that make the post timely
- **Platform awareness**: LinkedIn algorithm preferences, hashtag strategy, engagement patterns, timing, "see more" fold

### References (LinkedIn)
- **Inspiration posts**: Example posts, style references, viral post templates to emulate
- **Data/statistics**: Research, case studies, specific data points that ground the post in credibility
- **Expertise basis**: Personal experience, company data, proprietary insights that support the author's authority

### Constraints (LinkedIn)
- **Length/formatting**: ~1300 characters optimal, hook in first 2 lines (above the fold ~210 chars), line breaks for mobile readability
- **Tone boundaries**: Professional yet authentic, no hard selling, no clickbait
- **Content exclusions**: Competitor mentions, controversial topics, confidential information
- **Hashtag/mention requirements**: 3-5 niche hashtags, @mentions, branded hashtags

### LinkedIn scoring guidance:
- 81-100: Post objective, voice, audience, author identity, platform awareness, references, and all constraints specified
- 61-80: Good audience and voice but missing example posts, hashtag strategy, or length constraints
- 41-60: Topic specified but no audience targeting, no hook guidance, no CTA
- 21-40: Just "write a LinkedIn post" with no specifics
- 0-20: No discernible LinkedIn post objective

## Iterate

The Iterate flag indicates whether the prompt is structured for iterative refinement — i.e., it's specific enough that the output can be meaningfully evaluated and the prompt can be improved based on results.
