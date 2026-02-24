"""Change embedding vector dimension from 512 to 768 for Ollama nomic-embed-text.

Revision ID: 002
Revises: 001
Create Date: 2026-02-19
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the IVFFlat index (depends on the column type)
    op.drop_index("idx_conv_embeddings_vector", table_name="conversation_embeddings")

    # Delete existing embeddings — old 512-dim vectors are incompatible with 768-dim
    op.execute(sa.text("TRUNCATE TABLE conversation_embeddings"))

    # Alter column to vector(768)
    op.alter_column(
        "conversation_embeddings",
        "embedding",
        type_=Vector(768),
        existing_nullable=False,
    )

    # Recreate IVFFlat index
    op.create_index(
        "idx_conv_embeddings_vector",
        "conversation_embeddings",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_with={"lists": 100},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("idx_conv_embeddings_vector", table_name="conversation_embeddings")

    op.execute(sa.text("TRUNCATE TABLE conversation_embeddings"))

    op.alter_column(
        "conversation_embeddings",
        "embedding",
        type_=Vector(512),
        existing_nullable=False,
    )

    op.create_index(
        "idx_conv_embeddings_vector",
        "conversation_embeddings",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_with={"lists": 100},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
