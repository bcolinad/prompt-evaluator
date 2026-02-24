"""Repository pattern for database operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Document, DocumentChunkRecord, EvalConfig, Evaluation
from src.evaluator import EvaluationResult, FullEvaluationReport


class EvaluationRepository:
    """CRUD operations for evaluations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(
        self,
        result: EvaluationResult,
        session_id: str,
        full_report: FullEvaluationReport | None = None,
        thread_id: str | None = None,
    ) -> Evaluation:
        """Persist an evaluation result to the database."""
        dim_scores = {d.name: d.score for d in result.dimensions}

        eval_phase = None
        llm_output = None
        output_evaluation = None
        langsmith_run_id = None

        if full_report is not None:
            eval_phase = full_report.phase.value
            if full_report.output_result is not None:
                llm_output = full_report.output_result.llm_output
                output_evaluation = full_report.output_result.model_dump()
                langsmith_run_id = full_report.output_result.langsmith_run_id

        evaluation = Evaluation(
            id=result.id,
            session_id=session_id,
            thread_id=thread_id,
            mode=result.mode.value,
            input_text=result.input_text,
            expected_outcome=result.expected_outcome,
            overall_score=result.overall_score,
            grade=result.grade.value,
            task_score=dim_scores.get("task"),
            context_score=dim_scores.get("context"),
            references_score=dim_scores.get("references"),
            constraints_score=dim_scores.get("constraints"),
            analysis=result.model_dump(include={"dimensions", "tcrei_flags"}),
            improvements=[imp.model_dump() for imp in result.improvements],
            rewritten_prompt=result.rewritten_prompt,
            eval_phase=eval_phase,
            llm_output=llm_output,
            output_evaluation=output_evaluation,
            langsmith_run_id=langsmith_run_id,
        )

        self.session.add(evaluation)
        await self.session.flush()
        return evaluation

    async def get_by_id(self, evaluation_id: UUID) -> Evaluation | None:
        """Retrieve an evaluation by ID."""
        result = await self.session.execute(
            select(Evaluation).where(Evaluation.id == evaluation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_session(self, session_id: str, limit: int = 20) -> list[Evaluation]:
        """Retrieve evaluations for a session, ordered by most recent."""
        result = await self.session.execute(
            select(Evaluation)
            .where(Evaluation.session_id == session_id)
            .order_by(Evaluation.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class ConfigRepository:
    """CRUD operations for evaluation configs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_default(self) -> EvalConfig | None:
        """Get the default evaluation configuration."""
        result = await self.session.execute(
            select(EvalConfig).where(EvalConfig.is_default.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> EvalConfig | None:
        """Get a configuration by name."""
        result = await self.session.execute(
            select(EvalConfig).where(EvalConfig.name == name)
        )
        return result.scalar_one_or_none()


class DocumentRepository:
    """CRUD operations for documents and document chunks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Retrieve a document by ID."""
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_by_thread(self, thread_id: str, limit: int = 50) -> list[Document]:
        """Retrieve documents for a thread, ordered by most recent."""
        result = await self.session.execute(
            select(Document)
            .where(Document.thread_id == thread_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user(self, user_id: str, limit: int = 50) -> list[Document]:
        """Retrieve documents for a user, ordered by most recent."""
        result = await self.session.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_by_thread(self, thread_id: str) -> int:
        """Delete all documents and their chunks for a thread.

        Returns:
            Number of documents deleted.
        """
        # Chunks cascade-delete via FK, but also delete explicitly for safety
        await self.session.execute(
            delete(DocumentChunkRecord).where(DocumentChunkRecord.thread_id == thread_id)
        )
        result = await self.session.execute(
            delete(Document).where(Document.thread_id == thread_id)
        )
        return result.rowcount  # type: ignore[return-value]
