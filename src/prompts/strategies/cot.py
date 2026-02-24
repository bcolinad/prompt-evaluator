"""Chain-of-Thought (CoT) preamble for the analysis node.

This preamble is prepended to the existing analysis system prompt when
CoT strategy is active, instructing the LLM to reason step-by-step
through each T.C.R.E.I. dimension before producing the JSON output.
"""

COT_ANALYSIS_PREAMBLE = """## Chain-of-Thought Analysis Instructions

Before producing your JSON evaluation, you MUST reason step-by-step through each dimension.
Work through the following steps explicitly in your thinking:

STEP 1 — TASK DIMENSION: Identify the action verb, specific deliverable, persona, and output format.
Ask yourself: "What exactly is the user asking the AI to DO?" List each sub-criterion and whether
it is present or absent in the prompt, with evidence.

STEP 2 — CONTEXT DIMENSION: Identify background information, audience, goals, and domain specificity.
Ask yourself: "Does the prompt provide enough situational context for the AI to tailor its response?"
List each sub-criterion with evidence.

STEP 3 — REFERENCES DIMENSION: Identify examples, structured references, and labeled materials.
Ask yourself: "Are there any examples, templates, or reference materials that guide the AI's output?"
List each sub-criterion with evidence.

STEP 4 — CONSTRAINTS DIMENSION: Identify scope boundaries, length limits, format restrictions, and exclusions.
Ask yourself: "What guardrails or limitations are placed on the AI's response?" List each sub-criterion
with evidence.

STEP 5 — TCREI FLAGS: Based on your analysis in Steps 1-4, determine which of the five T.C.R.E.I.
components (Task, Context, References, Evaluate, Iterate) are meaningfully present in the prompt.

After completing all five steps, produce your JSON evaluation with scores and sub-criteria findings
that reflect your step-by-step reasoning.

---

"""
