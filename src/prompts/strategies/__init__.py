"""Strategy prompt templates for advanced evaluation techniques.

Re-exports all strategy prompt constants for convenient importing.
"""

from src.prompts.strategies.cot import COT_ANALYSIS_PREAMBLE
from src.prompts.strategies.meta import META_EVALUATION_PROMPT
from src.prompts.strategies.tot import TOT_BRANCH_GENERATION_PROMPT, TOT_BRANCH_SELECTION_PROMPT

__all__ = [
    "COT_ANALYSIS_PREAMBLE",
    "META_EVALUATION_PROMPT",
    "TOT_BRANCH_GENERATION_PROMPT",
    "TOT_BRANCH_SELECTION_PROMPT",
]
