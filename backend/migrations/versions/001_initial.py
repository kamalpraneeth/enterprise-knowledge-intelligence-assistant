"""
Initial migration: create all tables with pgvector support.

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- users ---
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'knowledge_manager', 'employee')")
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", postgresql.ENUM("admin", "knowledge_manager", "employee", name="user_role", create_type=False), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # --- documents ---
    op.execute("CREATE TYPE document_status AS ENUM ('pending', 'processing', 'indexed', 'failed', 'deleted')")
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", postgresql.ENUM("pending", "processing", "indexed", "failed", "deleted", name="document_status", create_type=False), nullable=False),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("chunk_count", sa.Integer, nullable=True, default=0),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- document_chunks ---
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("section_title", sa.String(512), nullable=True),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column("embedding", sa.String, nullable=True),  # Placeholder, will use vector type via raw SQL
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Add the actual vector column
    op.execute("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_vec vector(768)")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE document_chunks RENAME COLUMN embedding_vec TO embedding")
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    # --- messages ---
    op.execute("CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system')")
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", postgresql.ENUM("user", "assistant", "system", name="message_role", create_type=False), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("retrieval_latency_ms", sa.Float, nullable=True),
        sa.Column("generation_latency_ms", sa.Float, nullable=True),
        sa.Column("total_latency_ms", sa.Float, nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("has_sufficient_evidence", sa.Boolean, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    # --- citations ---
    op.create_table(
        "citations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("chunk_id", sa.String(36), sa.ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("document_name", sa.String(512), nullable=True),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("section_title", sa.String(512), nullable=True),
        sa.Column("passage", sa.Text, nullable=True),
        sa.Column("similarity_score", sa.Float, nullable=True),
        sa.Column("rank", sa.Integer, nullable=False, default=1),
    )
    op.create_index("ix_citations_message_id", "citations", ["message_id"])

    # --- tool_executions ---
    op.execute("CREATE TYPE tool_status AS ENUM ('pending', 'success', 'error', 'skipped')")
    op.create_table(
        "tool_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("input_args", postgresql.JSONB, nullable=True),
        sa.Column("output", postgresql.JSONB, nullable=True),
        sa.Column("status", postgresql.ENUM("pending", "success", "error", "skipped", name="tool_status", create_type=False), nullable=False),
        sa.Column("duration_ms", sa.Float, nullable=True),
        sa.Column("error_category", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- user_feedback ---
    op.create_table(
        "user_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(36), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- audit_events ---
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    # --- evaluation_datasets ---
    op.create_table(
        "evaluation_datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("question_count", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- evaluation_questions ---
    op.create_table(
        "evaluation_questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("reference_answer", sa.Text, nullable=True),
        sa.Column("expected_document_ids", postgresql.JSONB, nullable=True),
        sa.Column("question_type", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- evaluation_runs ---
    op.execute("CREATE TYPE eval_run_status AS ENUM ('pending', 'running', 'completed', 'failed')")
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("evaluation_datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", postgresql.ENUM("pending", "running", "completed", "failed", name="eval_run_status", create_type=False), nullable=False, default="pending"),
        sa.Column("total_questions", sa.Integer, default=0),
        sa.Column("completed_questions", sa.Integer, default=0),
        sa.Column("avg_retrieval_precision", sa.Float, nullable=True),
        sa.Column("avg_answer_correctness", sa.Float, nullable=True),
        sa.Column("avg_citation_accuracy", sa.Float, nullable=True),
        sa.Column("insufficient_evidence_rate", sa.Float, nullable=True),
        sa.Column("avg_latency_ms", sa.Float, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("prompt_version", sa.String(50), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- evaluation_results ---
    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.String(36), sa.ForeignKey("evaluation_questions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("generated_answer", sa.Text, nullable=True),
        sa.Column("retrieval_precision", sa.Float, nullable=True),
        sa.Column("answer_correctness", sa.Float, nullable=True),
        sa.Column("citation_correct", sa.Boolean, nullable=True),
        sa.Column("has_sufficient_evidence", sa.Boolean, nullable=True),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
    op.execute("DROP TYPE IF EXISTS eval_run_status")
    op.drop_table("evaluation_questions")
    op.drop_table("evaluation_datasets")
    op.drop_table("audit_events")
    op.drop_table("user_feedback")
    op.drop_table("tool_executions")
    op.execute("DROP TYPE IF EXISTS tool_status")
    op.drop_table("citations")
    op.drop_table("messages")
    op.execute("DROP TYPE IF EXISTS message_role")
    op.drop_table("conversations")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.execute("DROP TYPE IF EXISTS document_status")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS user_role")
