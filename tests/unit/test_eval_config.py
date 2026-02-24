"""Unit tests for evaluation configuration loading and scoring."""


from src.config.eval_config import GradingScale


class TestEvalConfig:
    def test_load_default_config(self, eval_config):
        assert "task" in eval_config.dimensions
        assert "context" in eval_config.dimensions
        assert "references" in eval_config.dimensions
        assert "constraints" in eval_config.dimensions

    def test_weights_sum_to_one(self, eval_config):
        total = sum(d.weight for d in eval_config.dimensions.values())
        assert abs(total - 1.0) < 0.01

    def test_compute_overall_weighted(self, eval_config):
        scores = {"task": 100, "context": 100, "references": 100, "constraints": 100}
        assert eval_config.compute_overall(scores) == 100

    def test_compute_overall_zero(self, eval_config):
        scores = {"task": 0, "context": 0, "references": 0, "constraints": 0}
        assert eval_config.compute_overall(scores) == 0

    def test_compute_overall_mixed(self, eval_config):
        scores = {"task": 80, "context": 60, "references": 0, "constraints": 40}
        overall = eval_config.compute_overall(scores)
        assert 0 < overall < 100

    def test_get_grade_excellent(self, eval_config):
        assert eval_config.get_grade(90) == "Excellent"

    def test_get_grade_good(self, eval_config):
        assert eval_config.get_grade(70) == "Good"

    def test_get_grade_needs_work(self, eval_config):
        assert eval_config.get_grade(50) == "Needs Work"

    def test_get_grade_weak(self, eval_config):
        assert eval_config.get_grade(20) == "Weak"

    def test_grade_boundaries(self, eval_config):
        assert eval_config.get_grade(85) == "Excellent"
        assert eval_config.get_grade(84) == "Good"
        assert eval_config.get_grade(65) == "Good"
        assert eval_config.get_grade(64) == "Needs Work"
        assert eval_config.get_grade(40) == "Needs Work"
        assert eval_config.get_grade(39) == "Weak"
        assert eval_config.get_grade(0) == "Weak"


class TestGradingScale:
    def test_default_values(self):
        scale = GradingScale()
        assert scale.excellent == 85
        assert scale.good == 65
        assert scale.needs_work == 40
        assert scale.weak == 0

    def test_custom_values(self):
        scale = GradingScale(excellent=90, good=70, needs_work=50, weak=0)
        assert scale.excellent == 90
