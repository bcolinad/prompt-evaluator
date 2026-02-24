"""Add documents and document_chunks tables for document processing.

Revision ID: 004
Revises: 003
Create Date: 2026-02-23
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=True, index=True),
        sa.Column("thread_id", sa.String(255), nullable=True, index=True),
        sa.Column("session_id", sa.String(255), nullable=True, index=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("extractions", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("processing_time_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "document_id", sa.UUID(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("thread_id", sa.String(255), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_title", sa.String(512), nullable=True),
        sa.Column("char_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Indexes for document_chunks
    op.create_index("idx_doc_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("idx_doc_chunks_user_id", "document_chunks", ["user_id"])
    op.create_index("idx_doc_chunks_thread_id", "document_chunks", ["thread_id"])

    # HNSW index for cosine similarity search on embeddings
    op.execute(
        "CREATE INDEX idx_doc_chunks_embedding ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("idx_doc_chunks_embedding", table_name="document_chunks")
    op.drop_index("idx_doc_chunks_thread_id", table_name="document_chunks")
    op.drop_index("idx_doc_chunks_user_id", table_name="document_chunks")
    op.drop_index("idx_doc_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("documents")
