"""Email-specific evaluation criteria."""

from __future__ import annotations

from src.evaluator.criteria.base import Criterion

EMAIL_TASK_CRITERIA = [
    Criterion(
        name="email_action_specified",
        description="The prompt specifies the type of email action: write, reply, follow up, draft, forward, or compose",
        detection_hint="Look for verbs: write an email, draft a reply, compose a follow-up, respond to, send a message, craft an email",
        weight=0.25,
    ),
    Criterion(
        name="tone_style_defined",
        description="The prompt specifies the desired tone and writing style for the email (formal, casual, persuasive, empathetic, urgent, diplomatic)",
        detection_hint="Look for: 'formal tone', 'casual', 'friendly but professional', 'empathetic', 'direct', 'persuasive', 'apologetic', 'warm', 'firm but polite'",
        weight=0.30,
    ),
    Criterion(
        name="email_purpose_clear",
        description="The prompt clearly states what the email should accomplish: inform, request, persuade, apologize, confirm, introduce, follow up",
        detection_hint="Look for: 'to request', 'to inform them about', 'asking for', 'to apologize', 'to schedule', 'to follow up on', 'to confirm'",
        weight=0.25,
    ),
    Criterion(
        name="email_structure_specified",
        description="The prompt specifies email structural elements: subject line, greeting style, closing, signature, or overall format",
        detection_hint="Look for: 'include a subject line', 'professional greeting', 'sign off with', 'include a call to action', 'bullet points in the body', 'keep it to one paragraph'",
        weight=0.20,
    ),
]

EMAIL_CONTEXT_CRITERIA = [
    Criterion(
        name="recipient_defined",
        description="The prompt specifies who will receive the email: their role, relationship to the sender, or name",
        detection_hint="Look for: 'to my manager', 'to the client', 'to the team', 'to a potential employer', 'to the HR department', specific names or titles",
        weight=0.30,
    ),
    Criterion(
        name="sender_context_provided",
        description="The prompt provides context about the sender's role, relationship, or situation",
        detection_hint="Look for: 'I am a...', 'as the project lead', 'I recently...', 'our company...', 'my role is...', context about the sender's position",
        weight=0.25,
    ),
    Criterion(
        name="situation_background",
        description="The prompt includes the background situation that prompted the email: what happened, what's needed, or the current status",
        detection_hint="Look for: 'regarding the...', 'after our meeting about...', 'following up on...', 'in response to...', 'the deadline is...', 'the project is...'",
        weight=0.25,
    ),
    Criterion(
        name="relationship_dynamic",
        description="The prompt indicates the formality level or relationship dynamic between sender and recipient",
        detection_hint="Look for: 'first-time contact', 'we have worked together', 'reporting to them', 'they are a new hire', 'long-standing client', 'cold outreach'",
        weight=0.20,
    ),
]

EMAIL_REFERENCES_CRITERIA = [
    Criterion(
        name="email_examples_provided",
        description="The prompt includes example emails, previous correspondence, or sample tone to emulate",
        detection_hint="Look for: 'here is a previous email', 'like this example', 'in the style of', pasted email threads, quoted text, 'similar to this email I sent'",
        weight=0.40,
    ),
    Criterion(
        name="key_points_listed",
        description="The prompt lists specific points, data, or topics that must be included in the email body",
        detection_hint="Look for: numbered lists of points to cover, 'mention these points', 'include the following information', specific data points, names, dates, figures",
        weight=0.35,
    ),
    Criterion(
        name="prior_thread_context",
        description="The prompt provides context from prior email exchanges or conversation history that the email should reference",
        detection_hint="Look for: 'they previously said...', 'in their last email...', 'we discussed...', 'the original thread was about...', forwarded content",
        weight=0.25,
    ),
]

EMAIL_CONSTRAINTS_CRITERIA = [
    Criterion(
        name="length_brevity",
        description="The prompt specifies email length constraints: brief, concise, one paragraph, under N sentences, or detailed",
        detection_hint="Look for: 'keep it brief', 'one paragraph', 'under 5 sentences', 'concise', 'detailed', 'short and direct', specific word/sentence count",
        weight=0.25,
    ),
    Criterion(
        name="formality_level",
        description="The prompt explicitly constrains the formality level: professional, semi-formal, casual, or specifies what to avoid",
        detection_hint="Look for: 'professional language', 'no slang', 'avoid jargon', 'semi-formal', 'casual tone', 'corporate language', 'avoid being too stiff'",
        weight=0.25,
    ),
    Criterion(
        name="content_exclusions",
        description="The prompt states what to avoid or exclude from the email: certain topics, phrases, information, or emotional tones",
        detection_hint="Look for: 'do not mention...', 'avoid bringing up...', 'don't sound desperate', 'no excuses', 'don't blame', 'avoid technical jargon', 'skip the pleasantries'",
        weight=0.25,
    ),
    Criterion(
        name="call_to_action_specified",
        description="The prompt specifies what action the recipient should take after reading, or what the desired next step is",
        detection_hint="Look for: 'ask them to...', 'request a meeting', 'they should reply with...', 'prompt them to approve', 'end with a question', 'include next steps'",
        weight=0.25,
    ),
]

EMAIL_CRITERIA = {
    "task": EMAIL_TASK_CRITERIA,
    "context": EMAIL_CONTEXT_CRITERIA,
    "references": EMAIL_REFERENCES_CRITERIA,
    "constraints": EMAIL_CONSTRAINTS_CRITERIA,
}
