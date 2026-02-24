# Scoring Rubrics — T.C.R.E.I. Prompt Evaluation

## Overall Grading Scale

| Grade | Score Range | Description |
|-------|------------|-------------|
| Excellent | 85-100 | All dimensions well-covered; minor polish only |
| Good | 65-84 | Most dimensions present with minor gaps |
| Needs Work | 40-64 | Key dimensions missing or underdeveloped |
| Weak | 0-39 | Minimal prompt structure; fundamental issues |

## Dimension Weights

### General (default)

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Task | 30% | Core intent must be clear for any useful output |
| Context | 25% | Background drives relevance and appropriateness |
| References | 20% | Examples dramatically improve output quality |
| Constraints | 25% | Boundaries prevent scope creep and ensure usability |

### LinkedIn Professional Post

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Task | 25% | Post objective/voice/format/CTA are important but straightforward |
| Context | 35% | Highest weight — LinkedIn posts depend heavily on audience targeting and author brand |
| References | 15% | Original content relies less on external references |
| Constraints | 25% | Platform-specific constraints (length, hashtags, tone) directly impact performance |

## Score Range Details

### 0-20: Absent
The dimension is completely missing. Examples:
- Task 0-20: "dogs" (no verb, no deliverable, no format)
- Context 0-20: No background, no audience, no purpose
- References 0-20: No examples, no templates, no reference material
- Constraints 0-20: No limits, no exclusions, no format requirements

### 21-40: Minimal
The dimension has a trace but is far too vague. Examples:
- Task 21-40: "Write something about dogs" (verb present, but no specific deliverable or format)
- Context 21-40: "for my class" (audience hinted but not specified)
- References 21-40: "like that article I read" (reference mentioned but not provided)
- Constraints 21-40: "keep it short" (vague length constraint only)

### 41-60: Partial
The dimension is partially present but lacks specificity. Examples:
- Task 41-60: "Write a blog post about dogs" (verb + deliverable, but no persona or format details)
- Context 41-60: "for pet owners who are new to dog ownership" (audience clear, but no goals or domain depth)
- References 41-60: "Here's an example: [block of text]" (example present but not structured or labeled)
- Constraints 41-60: "500 words, informal tone" (length + style, but no scope boundaries or exclusions)

### 61-80: Well-Defined
The dimension is well-developed with minor gaps. Examples:
- Task 61-80: "You are a veterinarian. Write a 500-word blog post about common puppy health issues, formatted as numbered tips" (persona + deliverable + format, but no explicit output structure)
- Context 61-80: "This is for new puppy owners visiting our clinic website. The goal is to educate them on preventive care" (audience + goals + domain, but limited background)
- References 61-80: "<example>Here's how tip #1 should look: [formatted example]</example>" (structured example with label)
- Constraints 61-80: "Focus only on the first year. Avoid breed-specific advice. Keep it at a 6th-grade reading level" (scope + exclusion + style, but no explicit length)

### 81-100: Excellent
The dimension is comprehensive with all sub-criteria addressed. Examples:
- Task 81-100: Full persona, specific deliverable, exact output format with structure template
- Context 81-100: Rich background, named audience, clear goals, domain-specific terminology
- References 81-100: Multiple labeled examples with XML tags showing expected input/output pairs
- Constraints 81-100: Clear scope boundaries, length limits, exclusions, tone/style requirements

## Example Prompt Evaluations

### Weak Prompt (Score: ~15)
> "Tell me about machine learning"

- Task: 10 — No action verb beyond "tell", no deliverable, no persona, no format
- Context: 5 — No background, audience, goals, or domain
- References: 0 — No examples
- Constraints: 8 — No boundaries at all

### Needs Work Prompt (Score: ~50)
> "Write a summary of machine learning for beginners"

- Task: 55 — Clear verb "write", deliverable "summary", but no persona or format
- Context: 50 — Audience "beginners" present, but no background or goals
- References: 0 — No examples
- Constraints: 30 — Implied brevity ("summary") but no explicit limits

### Good Prompt (Score: ~75)
> "You are a data science instructor. Write a 500-word introduction to machine learning for college freshmen taking their first CS course. Include 3 real-world examples. Use simple analogies and avoid mathematical notation."

- Task: 85 — Persona, deliverable, word count, audience
- Context: 75 — Audience well-defined, educational setting, but limited background on course
- References: 45 — "3 real-world examples" mentioned but not provided
- Constraints: 80 — Length limit, exclusion (no math), style (simple analogies)

### Excellent Prompt (Score: ~92)
> "You are a senior data science instructor at a liberal arts college. Write a 500-word introduction to machine learning for freshman students in 'CS 101: Computing for Everyone' — a course designed for non-CS majors.
>
> <audience>Students have no prior programming experience and may be anxious about technical content. They are motivated by seeing how CS connects to their majors (art, psychology, biology).</audience>
>
> <example_output>The introduction should read like this opening paragraph: 'Imagine you're sorting your photo library...'</example_output>
>
> Requirements:
> - Use 3 analogies from everyday life (cooking, music, or sports preferred)
> - Avoid all mathematical notation, code snippets, and technical jargon
> - End with 2 reflection questions students can discuss in small groups
> - Format: Title + 4 short paragraphs + discussion questions
> - Reading level: 8th grade or below"

- Task: 95 — Specific persona, deliverable, exact format, clear structure
- Context: 95 — Rich audience profile, course context, student motivation, domain specificity
- References: 85 — Structured example with XML tags, preferred analogy domains
- Constraints: 90 — Clear exclusions, length, format, reading level, specific requirements
