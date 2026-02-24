"""Example prompts with annotated T.C.R.E.I. breakdowns for each task type.

Provides pre-built example prompts that demonstrate strong prompt structure,
with annotated sections mapping each part to T.C.R.E.I. dimensions. Used by
the Chainlit UI to show users what a well-crafted prompt looks like.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.evaluator import TaskType


@dataclass(frozen=True)
class AnnotatedSection:
    """A single annotated section of an example prompt.

    Attributes:
        dimension: The T.C.R.E.I. dimension this section demonstrates (e.g. "Task").
        label: Short label for the section (e.g. "Clear Action + Deliverable").
        text: The excerpt from the prompt that demonstrates this dimension.
        explanation: Why this section scores well for this dimension.
    """

    dimension: str
    label: str
    text: str
    explanation: str


@dataclass(frozen=True)
class ExamplePrompt:
    """A complete example prompt with T.C.R.E.I. annotations.

    Attributes:
        title: Display title for the example.
        full_prompt: The complete example prompt text.
        overall_description: Brief description of what makes this prompt strong.
        sections: List of annotated sections mapping prompt parts to dimensions.
        estimated_score: Estimated T.C.R.E.I. score (0-100) for this prompt.
    """

    title: str
    full_prompt: str
    overall_description: str
    sections: list[AnnotatedSection]
    estimated_score: int


# ── General Task Example ─────────────────────────────────────────────────────

_GENERAL_EXAMPLE = ExamplePrompt(
    title="Veterinarian Blog Article",
    full_prompt=(
        "You're a veterinarian writing for a pet owner blog aimed at first-time dog owners. "
        "Write a 500-word article about the top 5 health concerns for senior dogs (ages 8+), "
        "including early symptoms to watch for and when to visit the vet.\n\n"
        "Use a friendly, accessible tone — avoid medical jargon. Format as numbered sections "
        "with a brief intro paragraph. Reference the AVMA guidelines on senior pet care.\n\n"
        "Constraints: Focus only on large breed dogs (50+ lbs). Do not include dietary "
        "supplement recommendations."
    ),
    overall_description=(
        "This prompt covers all four T.C.R.E.I. dimensions: it assigns a persona and "
        "specifies a clear deliverable (Task), provides audience and domain context "
        "(Context), includes a concrete reference source (References), and sets scope "
        "boundaries with explicit exclusions (Constraints)."
    ),
    sections=[
        AnnotatedSection(
            dimension="Task",
            label="Persona + Action + Deliverable",
            text=(
                "You're a veterinarian writing for a pet owner blog aimed at first-time "
                "dog owners. Write a 500-word article about the top 5 health concerns for "
                "senior dogs (ages 8+), including early symptoms to watch for and when to "
                "visit the vet."
            ),
            explanation=(
                "Assigns a clear persona (veterinarian), uses a strong action verb (Write), "
                "specifies the exact deliverable (500-word article), and defines the output "
                "format (top 5 list with symptoms and vet visit guidance)."
            ),
        ),
        AnnotatedSection(
            dimension="Context",
            label="Audience + Domain",
            text=(
                "writing for a pet owner blog aimed at first-time dog owners"
            ),
            explanation=(
                "Defines the target audience (first-time dog owners), the publishing "
                "context (pet owner blog), and narrows the domain (senior dogs ages 8+)."
            ),
        ),
        AnnotatedSection(
            dimension="References",
            label="Source Material",
            text="Reference the AVMA guidelines on senior pet care.",
            explanation=(
                "Provides a specific, authoritative reference source (AVMA guidelines) "
                "that grounds the content in established veterinary standards."
            ),
        ),
        AnnotatedSection(
            dimension="Constraints",
            label="Scope Boundaries + Exclusions",
            text=(
                "Focus only on large breed dogs (50+ lbs). Do not include dietary "
                "supplement recommendations."
            ),
            explanation=(
                "Sets clear scope boundaries (large breeds only), defines an explicit "
                "exclusion (no supplement recommendations), and the format constraint "
                "(friendly tone, no jargon, numbered sections) limits stylistic drift."
            ),
        ),
    ],
    estimated_score=88,
)


# ── Email Creation Example ───────────────────────────────────────────────────

_EMAIL_EXAMPLE = ExamplePrompt(
    title="Professional Follow-Up Email",
    full_prompt=(
        "Draft a professional follow-up email to my project manager, Sarah Chen, "
        "regarding the Q3 budget proposal I submitted last Friday. I'm the marketing "
        "team lead and need her approval before the board meeting next Wednesday.\n\n"
        "Tone: polite but direct, with slight urgency. Reference our discussion from "
        "the Monday standup where she asked for revised cost projections.\n\n"
        "Include a clear call-to-action asking her to review and approve by end of day "
        "Tuesday. Keep the email under 150 words. Do not mention the competing proposal "
        "from the sales team."
    ),
    overall_description=(
        "This email prompt demonstrates all four dimensions with email-specific criteria: "
        "it specifies the email action and tone (Task), identifies the recipient and sender "
        "relationship (Context), references prior conversation context (References), and "
        "sets length limits with content exclusions (Constraints)."
    ),
    sections=[
        AnnotatedSection(
            dimension="Task",
            label="Email Action + Tone + Purpose",
            text=(
                "Draft a professional follow-up email to my project manager, Sarah Chen, "
                "regarding the Q3 budget proposal I submitted last Friday."
            ),
            explanation=(
                "Specifies the email action (draft a follow-up), identifies the tone "
                "(professional), and states the clear purpose (get approval on a budget "
                "proposal). The email type and objective are immediately clear."
            ),
        ),
        AnnotatedSection(
            dimension="Context",
            label="Recipient + Sender + Situation",
            text=(
                "I'm the marketing team lead and need her approval before the board "
                "meeting next Wednesday."
            ),
            explanation=(
                "Defines the sender's role (marketing team lead), the recipient's role "
                "(project manager), and the urgency context (board meeting deadline). "
                "The relationship dynamic (reporting to manager) is implicit."
            ),
        ),
        AnnotatedSection(
            dimension="References",
            label="Prior Thread Context",
            text=(
                "Reference our discussion from the Monday standup where she asked for "
                "revised cost projections."
            ),
            explanation=(
                "References a specific prior conversation (Monday standup) with concrete "
                "detail (revised cost projections), giving the AI context to write a "
                "natural continuation of an existing thread."
            ),
        ),
        AnnotatedSection(
            dimension="Constraints",
            label="Call-to-Action + Length + Exclusion",
            text=(
                "Include a clear call-to-action asking her to review and approve by end "
                "of day Tuesday. Keep the email under 150 words. Do not mention the "
                "competing proposal from the sales team."
            ),
            explanation=(
                "Specifies a concrete call-to-action (approve by Tuesday), sets a hard "
                "length limit (150 words), and defines an explicit content exclusion "
                "(no mention of the competing proposal)."
            ),
        ),
    ],
    estimated_score=91,
)


# ── Summarization Example ────────────────────────────────────────────────────

_SUMMARIZATION_EXAMPLE = ExamplePrompt(
    title="Research Paper Executive Summary",
    full_prompt=(
        "As a research analyst, summarize the attached 35-page WHO report on global "
        "antimicrobial resistance trends (2024) for a non-technical executive audience. "
        "The summary will be used as a briefing document for our VP of Product before "
        "a strategic planning meeting.\n\n"
        "Format: 5 bullet points covering the key findings, followed by a one-paragraph "
        "implications section. Target length: 250-300 words. Use plain language — avoid "
        "scientific jargon.\n\n"
        "Must include: the top 3 resistant pathogens mentioned and any regional data for "
        "North America. Do not editorialize or add interpretation beyond what the report "
        "states. Exclude the methodology section and statistical appendices."
    ),
    overall_description=(
        "This summarization prompt hits all four dimensions with summarization-specific "
        "criteria: it specifies the content scope and output format (Task), describes the "
        "source document and audience (Context), identifies the source material and key "
        "sections (References), and includes length limits with hallucination safeguards "
        "(Constraints)."
    ),
    sections=[
        AnnotatedSection(
            dimension="Task",
            label="Content Scope + Format + Persona",
            text=(
                "As a research analyst, summarize the attached 35-page WHO report on "
                "global antimicrobial resistance trends (2024) for a non-technical "
                "executive audience."
            ),
            explanation=(
                "Assigns a persona (research analyst), specifies the content scope "
                "(the entire WHO report), the summarization action (summarize), and "
                "the target reading level (non-technical). The format is further "
                "defined as bullet points plus a paragraph."
            ),
        ),
        AnnotatedSection(
            dimension="Context",
            label="Source Document + Audience + Purpose",
            text=(
                "The summary will be used as a briefing document for our VP of Product "
                "before a strategic planning meeting."
            ),
            explanation=(
                "Describes the source document (35-page WHO report, 2024), identifies "
                "the audience (VP of Product), and states the purpose (briefing for a "
                "strategic planning meeting) — anchoring the summary to something tangible."
            ),
        ),
        AnnotatedSection(
            dimension="References",
            label="Source Material + Key Sections",
            text=(
                "the attached 35-page WHO report on global antimicrobial resistance "
                "trends (2024)"
            ),
            explanation=(
                "References the specific source material (attached WHO report) with "
                "identifying details (35 pages, 2024, antimicrobial resistance). The "
                "inclusion requirements further identify key sections to prioritize "
                "(top 3 pathogens, North America data)."
            ),
        ),
        AnnotatedSection(
            dimension="Constraints",
            label="Length + Inclusions + Hallucination Safeguards",
            text=(
                "Target length: 250-300 words. Must include: the top 3 resistant "
                "pathogens mentioned and any regional data for North America. Do not "
                "editorialize or add interpretation beyond what the report states. "
                "Exclude the methodology section and statistical appendices."
            ),
            explanation=(
                "Sets a precise length target (250-300 words), specifies must-include "
                "elements (top 3 pathogens, North America data), adds hallucination "
                "safeguards (no editorializing, faithful to source), and defines "
                "exclusions (methodology, appendices)."
            ),
        ),
    ],
    estimated_score=93,
)


# ── Coding Task Example ─────────────────────────────────────────────────────

_CODING_EXAMPLE = ExamplePrompt(
    title="REST API Endpoint in Python",
    full_prompt=(
        "As a senior Python backend developer, write a FastAPI endpoint that accepts "
        "a JSON payload with a list of product IDs and returns their current inventory "
        "status from a PostgreSQL database.\n\n"
        "Requirements:\n"
        "- POST /api/v1/inventory/check\n"
        "- Input: {\"product_ids\": [\"SKU-001\", \"SKU-002\"]}\n"
        "- Output: {\"results\": [{\"id\": \"SKU-001\", \"in_stock\": true, \"quantity\": 42}]}\n"
        "- Use SQLAlchemy async with the existing `Product` model\n"
        "- Add Pydantic request/response models with type hints\n\n"
        "Constraints: Handle invalid SKUs with a 422 response. Add input validation "
        "for max 100 product IDs per request. Include error handling for database "
        "connection failures. Do not modify the existing Product model. Target "
        "response time under 200ms for 50 products."
    ),
    overall_description=(
        "This coding prompt covers all four T.C.R.E.I. dimensions: it specifies "
        "the language and architecture with a clear deliverable (Task), provides "
        "project context with existing codebase references (Context), includes "
        "input/output examples with API documentation (References), and sets "
        "performance, security, and scope constraints (Constraints)."
    ),
    sections=[
        AnnotatedSection(
            dimension="Task",
            label="Language + Architecture + Requirements",
            text=(
                "As a senior Python backend developer, write a FastAPI endpoint "
                "that accepts a JSON payload with a list of product IDs and returns "
                "their current inventory status from a PostgreSQL database."
            ),
            explanation=(
                "Specifies the language (Python), framework (FastAPI), persona "
                "(senior backend developer), deliverable (endpoint), and clear "
                "functional requirement (inventory status lookup)."
            ),
        ),
        AnnotatedSection(
            dimension="Context",
            label="Project Context + Existing Codebase",
            text=(
                "Use SQLAlchemy async with the existing Product model"
            ),
            explanation=(
                "References the existing codebase (Product model), specifies the "
                "ORM (SQLAlchemy async), and the database (PostgreSQL), providing "
                "integration context for the new code."
            ),
        ),
        AnnotatedSection(
            dimension="References",
            label="Input/Output Examples + API Spec",
            text=(
                "POST /api/v1/inventory/check\n"
                "Input: {\"product_ids\": [\"SKU-001\", \"SKU-002\"]}\n"
                "Output: {\"results\": [{\"id\": \"SKU-001\", \"in_stock\": true, \"quantity\": 42}]}"
            ),
            explanation=(
                "Provides the exact endpoint path, HTTP method, and concrete "
                "input/output JSON examples that serve as both API documentation "
                "and test case references."
            ),
        ),
        AnnotatedSection(
            dimension="Constraints",
            label="Error Handling + Performance + Scope",
            text=(
                "Handle invalid SKUs with a 422 response. Add input validation "
                "for max 100 product IDs per request. Target response time under "
                "200ms for 50 products. Do not modify the existing Product model."
            ),
            explanation=(
                "Sets clear error handling requirements (422 for invalid SKUs), "
                "input validation (max 100 IDs), performance target (200ms), "
                "and explicit scope exclusion (don't modify existing model)."
            ),
        ),
    ],
    estimated_score=90,
)


# ── Exam Interview Agent Example ────────────────────────────────────────────

_EXAM_EXAMPLE = ExamplePrompt(
    title="Technical Interview Assessment for Backend Engineers",
    full_prompt=(
        "As an experienced technical recruiter and software architect, create a "
        "60-minute technical interview assessment for mid-level backend engineer "
        "candidates (3-5 years experience) applying to our fintech startup.\n\n"
        "Structure: 3 sections\n"
        "- Section A: 10 multiple-choice questions on Python fundamentals and "
        "data structures (20 minutes, 2 points each)\n"
        "- Section B: 2 scenario-based coding problems testing API design and "
        "database optimization (30 minutes, 15 points each)\n"
        "- Section C: 1 system design question on payment processing architecture "
        "(10 minutes, 10 points)\n\n"
        "Include a scoring rubric with model answers for each question. Difficulty "
        "distribution: 30% easy, 50% medium, 20% hard. Reference the Python 3.11 "
        "documentation and REST API best practices.\n\n"
        "Constraints: Avoid questions requiring knowledge of proprietary frameworks. "
        "Ensure questions are culturally neutral and free from gender bias. Do not "
        "include trick questions or gotchas."
    ),
    overall_description=(
        "This exam/interview prompt covers all four T.C.R.E.I. dimensions: it "
        "defines the assessment objective with question types and difficulty (Task), "
        "describes the candidate profile and assessment context (Context), references "
        "documentation and assessment structure (References), and includes fairness "
        "safeguards with content exclusions (Constraints)."
    ),
    sections=[
        AnnotatedSection(
            dimension="Task",
            label="Assessment Objective + Question Design + Rubric",
            text=(
                "Create a 60-minute technical interview assessment for mid-level "
                "backend engineer candidates. Include a scoring rubric with model "
                "answers. Difficulty distribution: 30% easy, 50% medium, 20% hard."
            ),
            explanation=(
                "Defines the assessment type (technical interview), question "
                "formats (multiple-choice, scenario-based, system design), "
                "difficulty calibration (30/50/20 distribution), and requests "
                "a scoring rubric with model answers."
            ),
        ),
        AnnotatedSection(
            dimension="Context",
            label="Candidate Profile + Assessment Setting",
            text=(
                "mid-level backend engineer candidates (3-5 years experience) "
                "applying to our fintech startup"
            ),
            explanation=(
                "Specifies the candidate profile (mid-level, 3-5 years), the "
                "domain (fintech), the assessment context (job interview), and "
                "the time constraint (60 minutes)."
            ),
        ),
        AnnotatedSection(
            dimension="References",
            label="Source Material + Structure Template",
            text=(
                "Reference the Python 3.11 documentation and REST API best "
                "practices. Section A: 10 multiple-choice... Section B: 2 "
                "scenario-based... Section C: 1 system design..."
            ),
            explanation=(
                "References specific documentation (Python 3.11, REST best "
                "practices) and provides a detailed structural template with "
                "section breakdown, question counts, and point values."
            ),
        ),
        AnnotatedSection(
            dimension="Constraints",
            label="Fairness + Exclusions + Anti-Bias",
            text=(
                "Avoid questions requiring knowledge of proprietary frameworks. "
                "Ensure questions are culturally neutral and free from gender bias. "
                "Do not include trick questions or gotchas."
            ),
            explanation=(
                "Includes fairness safeguards (culturally neutral, gender-bias "
                "free), content exclusions (no proprietary frameworks), and "
                "anti-trick-question constraints."
            ),
        ),
    ],
    estimated_score=92,
)


# ── LinkedIn Professional Post Example ──────────────────────────────────────

_LINKEDIN_EXAMPLE = ExamplePrompt(
    title="Thought Leadership Post on AI in Hiring",
    full_prompt=(
        "As a VP of Talent Acquisition with 15 years in enterprise recruiting, write a "
        "LinkedIn thought leadership post sharing a contrarian take on AI-powered resume "
        "screening. Argue that over-reliance on AI screening is causing companies to miss "
        "exceptional candidates who don't fit traditional keyword patterns.\n\n"
        "Reference the 2024 Harvard Business School study showing that automated screening "
        "rejects 27% of qualified candidates. Draw from my experience leading hiring for "
        "3 Fortune 500 companies where we reduced mis-hires by 40% after supplementing "
        "AI screening with structured human review.\n\n"
        "Target audience: HR leaders, CHROs, and talent acquisition directors at mid-to-large "
        "enterprises. Writing voice: authoritative but conversational, using a storytelling "
        "approach with a data-driven backbone.\n\n"
        "Format: Text post, ~1300 characters. Start with a scroll-stopping hook that challenges "
        "conventional wisdom. Include 3 actionable alternatives to pure AI screening. End with "
        "an engagement question asking readers about their experience with AI screening failures.\n\n"
        "Constraints: Keep tone professional yet authentic — no hard selling of any product. "
        "Do not mention specific ATS vendors by name. Avoid generic advice. Include 4 niche "
        "hashtags related to talent acquisition and AI in HR. Use line breaks between paragraphs "
        "for mobile readability."
    ),
    overall_description=(
        "This LinkedIn post prompt covers all four T.C.R.E.I. dimensions: it defines the post "
        "objective, writing voice, content format, and CTA (Task), identifies the target audience "
        "and establishes author credibility (Context), references a specific study and personal "
        "experience data (References), and sets length, tone, exclusion, and hashtag constraints "
        "(Constraints)."
    ),
    sections=[
        AnnotatedSection(
            dimension="Task",
            label="Post Objective + Voice + Format + CTA",
            text=(
                "Write a LinkedIn thought leadership post sharing a contrarian take on "
                "AI-powered resume screening. Writing voice: authoritative but conversational, "
                "using a storytelling approach. Text post, ~1300 characters. Start with a "
                "scroll-stopping hook. End with an engagement question."
            ),
            explanation=(
                "Defines the post type (thought leadership), the writing voice (authoritative "
                "but conversational, storytelling with data), the format (text post), and a "
                "clear call to action (engagement question about AI screening failures)."
            ),
        ),
        AnnotatedSection(
            dimension="Context",
            label="Author Identity + Target Audience + Industry",
            text=(
                "As a VP of Talent Acquisition with 15 years in enterprise recruiting. "
                "Target audience: HR leaders, CHROs, and talent acquisition directors at "
                "mid-to-large enterprises."
            ),
            explanation=(
                "Establishes strong author credibility (VP title, 15 years experience, "
                "Fortune 500 background), precisely targets the audience (HR leaders, CHROs, "
                "TA directors), and provides industry context (AI in hiring is a current "
                "hot-button topic)."
            ),
        ),
        AnnotatedSection(
            dimension="References",
            label="Research Data + Personal Experience",
            text=(
                "Reference the 2024 Harvard Business School study showing that automated "
                "screening rejects 27% of qualified candidates. Draw from my experience "
                "leading hiring for 3 Fortune 500 companies where we reduced mis-hires by 40%."
            ),
            explanation=(
                "Cites a specific, authoritative study (HBS, 2024) with a concrete statistic "
                "(27% rejection rate), and provides personal credibility anchors (3 Fortune "
                "500 companies, 40% reduction in mis-hires) — combining external data with "
                "proprietary experience."
            ),
        ),
        AnnotatedSection(
            dimension="Constraints",
            label="Length + Tone + Exclusions + Hashtags",
            text=(
                "~1300 characters. Keep tone professional yet authentic — no hard selling. "
                "Do not mention specific ATS vendors by name. Include 4 niche hashtags "
                "related to talent acquisition and AI in HR. Use line breaks for mobile "
                "readability."
            ),
            explanation=(
                "Sets a precise length target (~1300 characters, optimal for LinkedIn), "
                "defines tone boundaries (professional, no selling), specifies content "
                "exclusions (no vendor names, no generic advice), and includes platform "
                "optimization (niche hashtags, line breaks for mobile)."
            ),
        ),
    ],
    estimated_score=90,
)


# ── Registry ─────────────────────────────────────────────────────────────────

EXAMPLE_PROMPTS: dict[TaskType, ExamplePrompt] = {
    TaskType.GENERAL: _GENERAL_EXAMPLE,
    TaskType.EMAIL_WRITING: _EMAIL_EXAMPLE,
    TaskType.SUMMARIZATION: _SUMMARIZATION_EXAMPLE,
    TaskType.CODING_TASK: _CODING_EXAMPLE,
    TaskType.EXAM_INTERVIEW: _EXAM_EXAMPLE,
    TaskType.LINKEDIN_POST: _LINKEDIN_EXAMPLE,
}


def get_example_for_task_type(task_type: TaskType) -> ExamplePrompt:
    """Return the example prompt for the given task type.

    Args:
        task_type: The task type to get an example for.

    Returns:
        The matching ExamplePrompt with annotated T.C.R.E.I. breakdown.
    """
    return EXAMPLE_PROMPTS[task_type]
