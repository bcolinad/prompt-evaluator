"""Unit tests for repository CRUD operations."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.db.repository import ConfigRepository, EvaluationRepository
from src.evaluator import DimensionScore, EvalMode, EvaluationResult, Grade, Improvement, Priority, TCREIFlags


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestEvaluationRepository:
    @pytest.mark.asyncio
    async def test_save(self, mock_session):
        repo = EvaluationRepository(mock_session)
        result = EvaluationResult(
            mode=EvalMode.PROMPT,
            input_text="Test prompt",
            overall_score=75,
            grade=Grade.GOOD,
            dimensions=[
                DimensionScore(name="task", score=80, sub_criteria=[]),
                DimensionScore(name="context", score=70, sub_criteria=[]),
                DimensionScore(name="references", score=60, sub_criteria=[]),
                DimensionScore(name="constraints", score=75, sub_criteria=[]),
            ],
            tcrei_flags=TCREIFlags(task=True, context=True),
            improvements=[
                Improvement(priority=Priority.MEDIUM, title="Test", suggestion="..."),
            ],
            rewritten_prompt="Better version",
        )

        evaluation = await repo.save(result, "session-123")

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert evaluation.session_id == "session-123"
        assert evaluation.mode == "prompt"
        assert evaluation.overall_score == 75

    @pytest.mark.asyncio
    async def test_save_with_thread_id(self, mock_session):
        repo = EvaluationRepository(mock_session)
        result = EvaluationResult(
            mode=EvalMode.PROMPT,
            input_text="Test prompt",
            overall_score=75,
            grade=Grade.GOOD,
            dimensions=[
                DimensionScore(name="task", score=80, sub_criteria=[]),
                DimensionScore(name="context", score=70, sub_criteria=[]),
                DimensionScore(name="references", score=60, sub_criteria=[]),
                DimensionScore(name="constraints", score=75, sub_criteria=[]),
            ],
            tcrei_flags=TCREIFlags(task=True, context=True),
            improvements=[],
        )

        evaluation = await repo.save(result, "session-456", thread_id="thread-abc")

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        assert evaluation.thread_id == "thread-abc"

    @pytest.mark.asyncio
    async def test_get_by_id(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id=uuid4())
        mock_session.execute.return_value = mock_result

        repo = EvaluationRepository(mock_session)
        evaluation = await repo.get_by_id(uuid4())

        mock_session.execute.assert_awaited_once()
        assert evaluation is not None

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = EvaluationRepository(mock_session)
        evaluation = await repo.get_by_id(uuid4())

        assert evaluation is None

    @pytest.mark.asyncio
    async def test_get_by_session(self, mock_session):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = EvaluationRepository(mock_session)
        evaluations = await repo.get_by_session("session-123")

        assert len(evaluations) == 2
        mock_session.execute.assert_awaited_once()


class TestConfigRepository:
    @pytest.mark.asyncio
    async def test_get_default(self, mock_session):
        mock_config = MagicMock()
        mock_config.name = "default"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        mock_session.execute.return_value = mock_result

        repo = ConfigRepository(mock_session)
        config = await repo.get_default()

        assert config is not None
        assert config.name == "default"

    @pytest.mark.asyncio
    async def test_get_default_not_found(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = ConfigRepository(mock_session)
        config = await repo.get_default()

        assert config is None

    @pytest.mark.asyncio
    async def test_get_by_name(self, mock_session):
        mock_config = MagicMock()
        mock_config.name = "healthcare"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_config
        mock_session.execute.return_value = mock_result

        repo = ConfigRepository(mock_session)
        config = await repo.get_by_name("healthcare")

        assert config.name == "healthcare"

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = ConfigRepository(mock_session)
        config = await repo.get_by_name("nonexistent")

        assert config is None
