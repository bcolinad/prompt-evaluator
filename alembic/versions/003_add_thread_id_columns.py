"""Add thread_id columns to evaluations and conversation_embeddings.

Enables cleanup of app data when a Chainlit thread is deleted.

Revision ID: 003
Revises: 002
Create Date: 2026-02-20
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add thread_id to evaluations
    op.add_column("evaluations", sa.Column("thread_id", sa.String(255), nullable=True))
    op.create_index("idx_evaluations_thread", "evaluations", ["thread_id"])

    # Add thread_id to conversation_embeddings
    op.add_column("conversation_embeddings", sa.Column("thread_id", sa.String(255), nullable=True))
    op.create_index("idx_conv_embeddings_thread", "conversation_embeddings", ["thread_id"])


def downgrade() -> None:
    op.drop_index("idx_conv_embeddings_thread", table_name="conversation_embeddings")
    op.drop_column("conversation_embeddings", "thread_id")

    op.drop_index("idx_evaluations_thread", table_name="evaluations")
    op.drop_column("evaluations", "thread_id")
