"""Unit tests for the composite improvement computation."""

from src.utils.report_generator import _compute_composite_improvement


class TestComputeCompositeImprovement:
    """Tests for _compute_composite_improvement()."""

    def test_all_engines_contribute(self) -> None:
        """All signals present — verify weighted formula."""
        result = _compute_composite_improvement(
            struct_score=55,
            output_score=60,
            opt_output_score=77,
            meta_confidence=0.87,
            tot_branch_confidence=0.82,
        )
        # structural_signal = (100 - 55) / 100 = 0.45
        # output_signal = max(0, 77 - 60) / 100 = 0.17
        # meta_signal = 0.87
        # tot_signal = 0.82
        # composite_raw = 0.45*0.25 + 0.17*0.35 + 0.87*0.20 + 0.82*0.20
        #               = 0.1125 + 0.0595 + 0.174 + 0.164 = 0.51
        assert result["composite_pct"] == 51
        assert result["structural_signal_pct"] == 45
        assert result["output_delta"] == 17
        assert result["output_delta_sign"] == "+"
        assert result["meta_confidence_pct"] == 87
        assert result["tot_confidence_pct"] == 82

    def test_no_meta_uses_default(self) -> None:
        """meta_confidence=None falls back to 0.5."""
        result = _compute_composite_improvement(
            struct_score=50,
            output_score=50,
            opt_output_score=70,
            meta_confidence=None,
            tot_branch_confidence=0.80,
        )
        assert result["meta_confidence_pct"] == 50
        # structural_signal = 0.50, output_signal = 0.20, meta = 0.50, tot = 0.80
        # 0.50*0.25 + 0.20*0.35 + 0.50*0.20 + 0.80*0.20
        # = 0.125 + 0.07 + 0.10 + 0.16 = 0.455 -> 46
        assert result["composite_pct"] == 46

    def test_no_tot_uses_default(self) -> None:
        """tot_branch_confidence=None falls back to 0.5."""
        result = _compute_composite_improvement(
            struct_score=50,
            output_score=50,
            opt_output_score=70,
            meta_confidence=0.80,
            tot_branch_confidence=None,
        )
        assert result["tot_confidence_pct"] == 50
        # structural_signal = 0.50, output_signal = 0.20, meta = 0.80, tot = 0.50
        # 0.50*0.25 + 0.20*0.35 + 0.80*0.20 + 0.50*0.20
        # = 0.125 + 0.07 + 0.16 + 0.10 = 0.455 -> 46
        assert result["composite_pct"] == 46

    def test_zero_output_delta_still_shows_other_engines(self) -> None:
        """opt == original but other engines still contribute."""
        result = _compute_composite_improvement(
            struct_score=40,
            output_score=70,
            opt_output_score=70,
            meta_confidence=0.90,
            tot_branch_confidence=0.85,
        )
        assert result["output_delta"] == 0
        assert result["output_delta_sign"] == "+"
        # structural_signal = 0.60, output_signal = 0.0, meta = 0.90, tot = 0.85
        # 0.60*0.25 + 0.0*0.35 + 0.90*0.20 + 0.85*0.20
        # = 0.15 + 0.0 + 0.18 + 0.17 = 0.50 -> 50
        assert result["composite_pct"] == 50

    def test_negative_output_delta_clamped_to_zero(self) -> None:
        """Optimized is worse — output signal clamped to 0."""
        result = _compute_composite_improvement(
            struct_score=50,
            output_score=80,
            opt_output_score=60,
            meta_confidence=0.70,
            tot_branch_confidence=0.60,
        )
        # raw_delta = 60 - 80 = -20, clamped to 0
        assert result["output_delta"] == 20  # abs value
        assert result["output_delta_sign"] == ""  # negative, no "+"
        # structural_signal = 0.50, output_signal = 0.0, meta = 0.70, tot = 0.60
        # 0.50*0.25 + 0.0*0.35 + 0.70*0.20 + 0.60*0.20
        # = 0.125 + 0.0 + 0.14 + 0.12 = 0.385 -> 38 (round)
        assert result["composite_pct"] == 38

    def test_perfect_scores(self) -> None:
        """All engines at max values."""
        result = _compute_composite_improvement(
            struct_score=0,  # 0 struct -> 100% gap signal
            output_score=0,
            opt_output_score=100,
            meta_confidence=1.0,
            tot_branch_confidence=1.0,
        )
        # structural_signal = 1.0, output_signal = 1.0, meta = 1.0, tot = 1.0
        # 1.0*0.25 + 1.0*0.35 + 1.0*0.20 + 1.0*0.20 = 1.0 -> 100
        assert result["composite_pct"] == 100
        assert result["structural_signal_pct"] == 100
        assert result["output_delta"] == 100
        assert result["meta_confidence_pct"] == 100
        assert result["tot_confidence_pct"] == 100

    def test_all_zeros(self) -> None:
        """Everything at minimum (struct=100 means 0 gap)."""
        result = _compute_composite_improvement(
            struct_score=100,  # perfect struct -> 0% gap signal
            output_score=50,
            opt_output_score=50,  # no improvement
            meta_confidence=0.0,
            tot_branch_confidence=0.0,
        )
        # structural_signal = 0.0, output_signal = 0.0, meta = 0.0, tot = 0.0
        # All zero -> composite = 0
        assert result["composite_pct"] == 0
        assert result["structural_signal_pct"] == 0
        assert result["output_delta"] == 0
        assert result["meta_confidence_pct"] == 0
        assert result["tot_confidence_pct"] == 0

    def test_both_none_defaults(self) -> None:
        """Both meta and tot are None — both default to 0.5."""
        result = _compute_composite_improvement(
            struct_score=60,
            output_score=50,
            opt_output_score=65,
            meta_confidence=None,
            tot_branch_confidence=None,
        )
        assert result["meta_confidence_pct"] == 50
        assert result["tot_confidence_pct"] == 50
        # structural_signal = 0.40, output_signal = 0.15
        # 0.40*0.25 + 0.15*0.35 + 0.50*0.20 + 0.50*0.20
        # = 0.10 + 0.0525 + 0.10 + 0.10 = 0.3525 -> 35
        assert result["composite_pct"] == 35
