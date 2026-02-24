"""LinkedIn professional post evaluation criteria."""

from __future__ import annotations

from src.evaluator.criteria.base import Criterion

LINKEDIN_TASK_CRITERIA = [
    Criterion(
        name="post_objective_defined",
        description="The prompt specifies the type of LinkedIn post to create: thought leadership, industry insight, personal story, how-to, announcement, or commentary",
        detection_hint="Look for: 'thought leadership post', 'share an insight about', 'personal story about', 'how-to post', 'announce', 'commentary on', 'opinion piece', 'career lesson', 'industry trend'",
        weight=0.30,
    ),
    Criterion(
        name="writing_voice_specified",
        description="The prompt specifies the desired writing voice or style: authoritative, conversational, storytelling, data-driven, provocative, or inspirational",
        detection_hint="Look for: 'authoritative tone', 'conversational', 'storytelling style', 'data-driven', 'provocative', 'inspirational', 'authentic voice', 'first-person', 'contrarian take', 'warm and approachable'",
        weight=0.25,
    ),
    Criterion(
        name="content_format_specified",
        description="The prompt specifies the content format: text post, carousel outline, poll, article, listicle, or story-based post",
        detection_hint="Look for: 'text post', 'carousel', 'poll', 'article', 'listicle', 'numbered list', 'story format', 'single image post', 'thread-style', 'short-form', 'long-form'",
        weight=0.25,
    ),
    Criterion(
        name="call_to_action_defined",
        description="The prompt specifies what action the audience should take: comment, share, visit a link, engage with a question, or tag someone",
        detection_hint="Look for: 'ask a question at the end', 'encourage comments', 'invite sharing', 'link to', 'tag someone', 'call to action', 'engagement question', 'what do you think?', 'agree or disagree?'",
        weight=0.20,
    ),
]

LINKEDIN_CONTEXT_CRITERIA = [
    Criterion(
        name="target_audience_specified",
        description="The prompt specifies who the post is targeting: industry, role, seniority level, or professional community",
        detection_hint="Look for: 'targeting HR leaders', 'for CTOs', 'aimed at marketers', 'startup founders', 'mid-career professionals', 'C-suite', 'hiring managers', 'developers', specific industry or role names",
        weight=0.30,
    ),
    Criterion(
        name="author_identity_defined",
        description="The prompt establishes the author's professional brand, expertise area, or credibility basis",
        detection_hint="Look for: 'I am a VP of', 'as a 10-year veteran', 'from my experience as', 'my background in', 'our company specializes in', 'thought leader in', professional title or credentials",
        weight=0.25,
    ),
    Criterion(
        name="industry_topic_context",
        description="The prompt provides context about industry trends, news hooks, or seasonal relevance that make the post timely",
        detection_hint="Look for: 'recent trend in', 'following the news about', 'this quarter', 'in light of', 'the current state of', 'emerging topic', 'hot debate about', references to current events or industry shifts",
        weight=0.25,
    ),
    Criterion(
        name="platform_awareness",
        description="The prompt shows awareness of LinkedIn's platform mechanics: algorithm preferences, hashtag strategy, engagement patterns, or timing",
        detection_hint="Look for: 'LinkedIn algorithm', 'hashtags', 'engagement', 'visibility', 'first 2 lines', 'hook', 'line breaks', 'emoji usage', 'posting time', 'dwell time', platform-specific formatting guidance",
        weight=0.20,
    ),
]

LINKEDIN_REFERENCES_CRITERIA = [
    Criterion(
        name="inspiration_posts_provided",
        description="The prompt includes example posts, style references, or viral post templates to emulate",
        detection_hint="Look for: 'like this post', 'in the style of', 'similar to', example post text, 'viral post format', 'here is an example', referenced LinkedIn influencers or post styles",
        weight=0.40,
    ),
    Criterion(
        name="data_statistics_referenced",
        description="The prompt references specific data points, research, case studies, or statistics to ground the post in credibility",
        detection_hint="Look for: 'cite the study', 'according to', 'research shows', 'data from', 'statistics', 'case study', 'survey results', 'report by', specific numbers or percentages",
        weight=0.30,
    ),
    Criterion(
        name="expertise_basis_specified",
        description="The prompt specifies the personal experience, company data, or credibility anchors that support the post's authority",
        detection_hint="Look for: 'from my experience', 'I have seen', 'our team found', 'in my 15 years', 'based on our company data', 'lessons I learned', 'mistakes I made', personal anecdotes or proprietary insights",
        weight=0.30,
    ),
]

LINKEDIN_CONSTRAINTS_CRITERIA = [
    Criterion(
        name="length_formatting_constraints",
        description="The prompt specifies character or word limits, hook requirements for the first 2 lines, line break formatting, or paragraph length",
        detection_hint="Look for: 'under 1300 characters', 'keep it concise', 'hook in the first 2 lines', 'short paragraphs', 'one sentence per line', 'line breaks between paragraphs', word or character count limits, 'above the fold'",
        weight=0.30,
    ),
    Criterion(
        name="tone_boundaries",
        description="The prompt sets tone boundaries: professional yet authentic, no hard selling, no clickbait, or specific emotional range",
        detection_hint="Look for: 'professional but authentic', 'no hard selling', 'avoid clickbait', 'genuine tone', 'not preachy', 'humble', 'avoid bragging', 'no corporate jargon', 'vulnerable but professional', tone restrictions",
        weight=0.25,
    ),
    Criterion(
        name="content_exclusions",
        description="The prompt explicitly states what to avoid: competitor mentions, controversial topics, confidential information, or sensitive subjects",
        detection_hint="Look for: 'do not mention competitors', 'avoid politics', 'no confidential information', 'exclude', 'stay away from', 'do not name', 'avoid controversial', content boundaries",
        weight=0.20,
    ),
    Criterion(
        name="hashtag_mention_requirements",
        description="The prompt specifies hashtag count, placement, or @mention requirements for the post",
        detection_hint="Look for: 'include 3-5 hashtags', 'niche hashtags', 'relevant hashtags', 'hashtag placement', '@mention', 'tag the company', 'branded hashtag', hashtag count or strategy",
        weight=0.25,
    ),
]

LINKEDIN_CRITERIA = {
    "task": LINKEDIN_TASK_CRITERIA,
    "context": LINKEDIN_CONTEXT_CRITERIA,
    "references": LINKEDIN_REFERENCES_CRITERIA,
    "constraints": LINKEDIN_CONSTRAINTS_CRITERIA,
}
