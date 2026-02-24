"""Tree-of-Thought (ToT) prompts for the improvement node.

ToT uses a two-phase approach:
1. **Divergent phase**: Generate N distinct improvement branches, each
   taking a different strategic approach to improving the prompt.
2. **Convergent phase**: Evaluate all branches and select the best one,
   or synthesize the strongest elements from multiple branches.
"""

TOT_BRANCH_GENERATION_PROMPT = """You are an expert prompt engineer generating diverse improvement strategies.

Given the original prompt and its evaluation results, generate exactly {num_branches} DISTINCT
improvement approaches. Each branch should take a fundamentally different strategic angle.

## Approaches to consider (pick {num_branches} different ones):
- **Structural Overhaul**: Reorganize the prompt with clear sections, headers, and logical flow
- **Persona & Context Enrichment**: Add rich persona definitions, audience context, and domain framing
- **Constraint & Format Engineering**: Add precise boundaries, output format specs, and guardrails
- **Example-Driven Enhancement**: Add concrete examples, templates, and reference patterns
- **Task Decomposition**: Break complex requests into clear sequential steps
- **Evaluation Criteria Injection**: Add self-assessment criteria the AI should check against

For each branch, provide:
1. A short description of the approach taken (1-2 sentences)
2. A list of specific improvements (with priority: CRITICAL, HIGH, MEDIUM, LOW)
3. A complete rewritten prompt implementing that approach
4. A confidence score (0.0-1.0) for how much this approach will improve the prompt

Original prompt:
```
{input_text}
```

Analysis results:
{analysis_summary}

Overall score: {overall_score}/100 ({grade})

Output quality analysis:
{output_quality_section}

Return your response as JSON with this structure:
{{
    "branches": [
        {{
            "approach": "description of this branch's strategy",
            "improvements": [
                {{"priority": "HIGH", "title": "improvement title", "suggestion": "detailed suggestion"}}
            ],
            "rewritten_prompt": "the complete rewritten prompt",
            "confidence": 0.85
        }}
    ]
}}
"""

TOT_BRANCH_SELECTION_PROMPT = """You are an expert prompt engineer evaluating multiple improvement strategies.

Review the following {num_branches} improvement branches for the original prompt and select the best one,
or synthesize the strongest elements from multiple branches into a superior prompt.

Original prompt:
```
{input_text}
```

Current score: {overall_score}/100 ({grade})

## Improvement Branches:
{branches_text}

## Your task:
1. Evaluate each branch's strengths and weaknesses
2. Select the best branch OR synthesize the best elements from multiple branches
3. Produce the final optimized prompt

Return your response as JSON:
{{
    "selected_branch_index": 0,
    "synthesized_prompt": "the final optimized prompt (synthesized from best elements)",
    "rationale": "why this branch/synthesis was chosen"
}}
"""
