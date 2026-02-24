"""Unit tests for SQLAlchemy ORM models."""

import uuid

from src.db.models import Base, ConversationEmbedding, EvalConfig, Evaluation


class TestEvaluationModel:
    def test_table_name(self):
        assert Evaluation.__tablename__ == "evaluations"

    def test_has_expected_columns(self):
        column_names = {c.name for c in Evaluation.__table__.columns}
        expected = {
            "id", "session_id", "thread_id", "mode", "input_text", "expected_outcome",
            "overall_score", "grade", "task_score", "context_score",
            "references_score", "constraints_score", "analysis",
            "improvements", "rewritten_prompt", "config_snapshot",
            "eval_phase", "llm_output", "output_evaluation", "langsmith_run_id",
            "created_at",
        }
        assert expected == column_names

    def test_primary_key_is_id(self):
        pk_cols = [c.name for c in Evaluation.__table__.primary_key.columns]
        assert pk_cols == ["id"]

    def test_instantiation(self):
        eval_obj = Evaluation(
            id=uuid.uuid4(),
            session_id="test-session",
            mode="prompt",
            input_text="Test prompt",
            overall_score=75,
            grade="Good",
            analysis={},
            improvements=[],
        )
        assert eval_obj.mode == "prompt"
        assert eval_obj.overall_score == 75

    def test_nullable_fields(self):
        eval_obj = Evaluation(
            id=uuid.uuid4(),
            session_id="s",
            mode="prompt",
            input_text="t",
            overall_score=0,
            grade="Weak",
            analysis={},
            improvements=[],
        )
        assert eval_obj.expected_outcome is None
        assert eval_obj.rewritten_prompt is None
        assert eval_obj.config_snapshot is None

    def test_new_output_columns_exist(self):
        column_names = {c.name for c in Evaluation.__table__.columns}
        assert "eval_phase" in column_names
        assert "llm_output" in column_names
        assert "output_evaluation" in column_names
        assert "langsmith_run_id" in column_names

    def test_new_output_columns_nullable(self):
        eval_obj = Evaluation(
            id=uuid.uuid4(),
            session_id="s",
            mode="prompt",
            input_text="t",
            overall_score=0,
            grade="Weak",
            analysis={},
            improvements=[],
        )
        assert eval_obj.eval_phase is None
        assert eval_obj.llm_output is None
        assert eval_obj.output_evaluation is None
        assert eval_obj.langsmith_run_id is None


class TestEvalConfigModel:
    def test_table_name(self):
        assert EvalConfig.__tablename__ == "eval_configs"

    def test_has_expected_columns(self):
        column_names = {c.name for c in EvalConfig.__table__.columns}
        expected = {"id", "name", "description", "config", "is_default", "created_at", "updated_at"}
        assert expected == column_names

    def test_primary_key_is_id(self):
        pk_cols = [c.name for c in EvalConfig.__table__.primary_key.columns]
        assert pk_cols == ["id"]

    def test_instantiation(self):
        config = EvalConfig(
            id=uuid.uuid4(),
            name="test-config",
            config={"dimensions": {}},
        )
        assert config.name == "test-config"


class TestConversationEmbeddingModel:
    def test_table_name(self):
        assert ConversationEmbedding.__tablename__ == "conversation_embeddings"

    def test_has_expected_columns(self):
        column_names = {c.name for c in ConversationEmbedding.__table__.columns}
        expected = {
            "id", "user_id", "thread_id", "evaluation_id", "input_text", "rewritten_prompt",
            "overall_score", "grade", "output_score", "improvements_summary",
            "embedding", "metadata", "created_at",
        }
        assert expected == column_names

    def test_primary_key_is_id(self):
        pk_cols = [c.name for c in ConversationEmbedding.__table__.primary_key.columns]
        assert pk_cols == ["id"]

    def test_instantiation(self):
        obj = ConversationEmbedding(
            input_text="Test prompt",
            overall_score=65,
            grade="Good",
            embedding=[0.1] * 1536,
        )
        assert obj.input_text == "Test prompt"
        assert obj.overall_score == 65
        assert obj.grade == "Good"

    def test_nullable_fields(self):
        obj = ConversationEmbedding(
            input_text="test",
            overall_score=0,
            grade="Weak",
            embedding=[0.0] * 1536,
        )
        assert obj.user_id is None
        assert obj.evaluation_id is None
        assert obj.rewritten_prompt is None
        assert obj.output_score is None
        assert obj.improvements_summary is None


class TestBase:
    def test_base_is_declarative(self):
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")
