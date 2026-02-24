"""Evaluation strategy types and configuration.

Defines the advanced prompting strategies (CoT, ToT, Meta Prompting) that
can be applied to the evaluation pipeline. Each strategy maps to a
``StrategyConfig`` that controls which enhancements are active.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class EvaluationStrategy(str, Enum):
    """Available evaluation strategy presets."""

    STANDARD = "standard"
    ENHANCED = "enhanced"
    COT_ONLY = "cot_only"
    TOT_ONLY = "tot_only"
    META_ONLY = "meta_only"


class StrategyConfig(BaseModel):
    """Configuration controlling which advanced strategies are active.

    Attributes:
        use_cot: Enable Chain-of-Thought reasoning in the analysis node.
        use_tot: Enable Tree-of-Thought branching in the improvement node.
        tot_num_branches: Number of parallel improvement branches for ToT.
        use_meta: Enable Meta Prompting self-evaluation node.
        meta_refinement_rounds: Number of meta-evaluation refinement rounds.
    """

    use_cot: bool = False
    use_tot: bool = False
    tot_num_branches: int = Field(default=3, ge=2, le=10)
    use_meta: bool = False
    meta_refinement_rounds: int = Field(default=1, ge=1, le=3)


def get_default_strategy() -> StrategyConfig:
    """Return the always-enhanced strategy config (CoT+ToT+Meta).

    Returns:
        A ``StrategyConfig`` with CoT, ToT, and Meta all enabled.
    """
    return StrategyConfig(use_cot=True, use_tot=True, use_meta=True)


def resolve_strategy(strategy: EvaluationStrategy) -> StrategyConfig:
    """Resolve an evaluation strategy preset into a concrete configuration.

    Args:
        strategy: The strategy preset to resolve.

    Returns:
        A ``StrategyConfig`` with the appropriate flags set.

    Raises:
        StrategyError: If the strategy value is not recognized.
    """
    from src.evaluator.exceptions import StrategyError

    mapping: dict[EvaluationStrategy, StrategyConfig] = {
        EvaluationStrategy.STANDARD: StrategyConfig(
            use_cot=False, use_tot=False, use_meta=False,
        ),
        EvaluationStrategy.ENHANCED: StrategyConfig(
            use_cot=True, use_tot=True, use_meta=True,
        ),
        EvaluationStrategy.COT_ONLY: StrategyConfig(
            use_cot=True, use_tot=False, use_meta=False,
        ),
        EvaluationStrategy.TOT_ONLY: StrategyConfig(
            use_cot=False, use_tot=True, use_meta=False,
        ),
        EvaluationStrategy.META_ONLY: StrategyConfig(
            use_cot=False, use_tot=False, use_meta=True,
        ),
    }

    config = mapping.get(strategy)
    if config is None:
        raise StrategyError(
            f"Unknown evaluation strategy: {strategy}",
            context={"strategy": str(strategy)},
        )
    return config
