"""Unit tests for the scorer node."""


import pytest

from src.agent.nodes.scorer import score_prompt
from src.evaluator import DimensionScore


class TestScorePrompt:
    @pytest.mark.asyncio
    async def test_weighted_scoring(self):
        state = {
            "dimension_scores": [
                DimensionScore(name="task", score=100, sub_criteria=[]),
                DimensionScore(name="context", score=100, sub_criteria=[]),
                DimensionScore(name="references", score=100, sub_criteria=[]),
                DimensionScore(name="constraints", score=100, sub_criteria=[]),
            ],
        }
        result = await score_prompt(state)
        assert result["overall_score"] == 100
        assert result["grade"] == "Excellent"
        assert result["current_step"] == "scoring_complete"

    @pytest.mark.asyncio
    async def test_zero_scores(self):
        state = {
            "dimension_scores": [
                DimensionScore(name="task", score=0, sub_criteria=[]),
                DimensionScore(name="context", score=0, sub_criteria=[]),
                DimensionScore(name="references", score=0, sub_criteria=[]),
                DimensionScore(name="constraints", score=0, sub_criteria=[]),
            ],
        }
        result = await score_prompt(state)
        assert result["overall_score"] == 0
        assert result["grade"] == "Weak"

    @pytest.mark.asyncio
    async def test_mixed_scores(self):
        state = {
            "dimension_scores": [
                DimensionScore(name="task", score=80, sub_criteria=[]),
                DimensionScore(name="context", score=60, sub_criteria=[]),
                DimensionScore(name="references", score=40, sub_criteria=[]),
                DimensionScore(name="constraints", score=70, sub_criteria=[]),
            ],
        }
        result = await score_prompt(state)
        # task: 80*0.3=24, context: 60*0.25=15, refs: 40*0.2=8, constraints: 70*0.25=17.5 = 64.5 → 65
        assert 60 <= result["overall_score"] <= 70
        assert result["grade"] in ("Good", "Needs Work")

    @pytest.mark.asyncio
    async def test_empty_dimensions(self):
        state = {"dimension_scores": []}
        result = await score_prompt(state)
        assert result["overall_score"] == 0
        assert result["grade"] == "Weak"

    @pytest.mark.asyncio
    async def test_no_dimensions_key(self):
        state = {}
        result = await score_prompt(state)
        assert result["overall_score"] == 0
        assert result["grade"] == "Weak"

    @pytest.mark.asyncio
    async def test_message_content(self):
        state = {
            "dimension_scores": [
                DimensionScore(name="task", score=90, sub_criteria=[]),
                DimensionScore(name="context", score=85, sub_criteria=[]),
                DimensionScore(name="references", score=70, sub_criteria=[]),
                DimensionScore(name="constraints", score=88, sub_criteria=[]),
            ],
        }
        result = await score_prompt(state)
        assert "messages" in result
        msg = result["messages"][0].content
        assert "Task: 90" in msg
        assert "Overall:" in msg
