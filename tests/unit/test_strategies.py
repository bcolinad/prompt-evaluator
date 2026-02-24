"""Unit tests for evaluation strategies."""

import pytest

from src.evaluator.strategies import (
    EvaluationStrategy,
    StrategyConfig,
    get_default_strategy,
    resolve_strategy,
)


class TestEvaluationStrategy:
    def test_standard_enum(self):
        assert EvaluationStrategy.STANDARD.value == "standard"

    def test_enhanced_enum(self):
        assert EvaluationStrategy.ENHANCED.value == "enhanced"

    def test_cot_only_enum(self):
        assert EvaluationStrategy.COT_ONLY.value == "cot_only"

    def test_tot_only_enum(self):
        assert EvaluationStrategy.TOT_ONLY.value == "tot_only"

    def test_meta_only_enum(self):
        assert EvaluationStrategy.META_ONLY.value == "meta_only"


class TestStrategyConfig:
    def test_defaults(self):
        config = StrategyConfig()
        assert config.use_cot is False
        assert config.use_tot is False
        assert config.use_meta is False
        assert config.tot_num_branches == 3
        assert config.meta_refinement_rounds == 1

    def test_all_enabled(self):
        config = StrategyConfig(use_cot=True, use_tot=True, use_meta=True)
        assert config.use_cot is True
        assert config.use_tot is True
        assert config.use_meta is True

    def test_tot_branches_range(self):
        config = StrategyConfig(tot_num_branches=5)
        assert config.tot_num_branches == 5

    def test_tot_branches_too_low(self):
        with pytest.raises(Exception):
            StrategyConfig(tot_num_branches=1)

    def test_tot_branches_too_high(self):
        with pytest.raises(Exception):
            StrategyConfig(tot_num_branches=11)

    def test_meta_rounds_range(self):
        config = StrategyConfig(meta_refinement_rounds=2)
        assert config.meta_refinement_rounds == 2

    def test_meta_rounds_too_low(self):
        with pytest.raises(Exception):
            StrategyConfig(meta_refinement_rounds=0)


class TestGetDefaultStrategy:
    def test_returns_all_enabled(self):
        config = get_default_strategy()
        assert config.use_cot is True
        assert config.use_tot is True
        assert config.use_meta is True

    def test_returns_strategy_config(self):
        config = get_default_strategy()
        assert isinstance(config, StrategyConfig)


class TestResolveStrategy:
    def test_standard(self):
        config = resolve_strategy(EvaluationStrategy.STANDARD)
        assert config.use_cot is False
        assert config.use_tot is False
        assert config.use_meta is False

    def test_enhanced(self):
        config = resolve_strategy(EvaluationStrategy.ENHANCED)
        assert config.use_cot is True
        assert config.use_tot is True
        assert config.use_meta is True

    def test_cot_only(self):
        config = resolve_strategy(EvaluationStrategy.COT_ONLY)
        assert config.use_cot is True
        assert config.use_tot is False
        assert config.use_meta is False

    def test_tot_only(self):
        config = resolve_strategy(EvaluationStrategy.TOT_ONLY)
        assert config.use_cot is False
        assert config.use_tot is True
        assert config.use_meta is False

    def test_meta_only(self):
        config = resolve_strategy(EvaluationStrategy.META_ONLY)
        assert config.use_cot is False
        assert config.use_tot is False
        assert config.use_meta is True

    def test_all_strategies_resolve(self):
        for strategy in EvaluationStrategy:
            config = resolve_strategy(strategy)
            assert isinstance(config, StrategyConfig)
