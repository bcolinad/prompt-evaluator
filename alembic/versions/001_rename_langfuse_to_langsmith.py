"""Add output evaluation columns with langsmith_run_id.

Revision ID: 001
Revises:
Create Date: 2026-02-18
"""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evaluations", sa.Column("eval_phase", sa.String(20), nullable=True))
    op.add_column("evaluations", sa.Column("llm_output", sa.Text(), nullable=True))
    op.add_column("evaluations", sa.Column("output_evaluation", sa.dialects.postgresql.JSONB(), nullable=True))
    op.add_column("evaluations", sa.Column("langsmith_run_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("evaluations", "langsmith_run_id")
    op.drop_column("evaluations", "output_evaluation")
    op.drop_column("evaluations", "llm_output")
    op.drop_column("evaluations", "eval_phase")
