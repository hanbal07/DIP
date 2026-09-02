"""initial schema with pgvector and core tables

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector for vector embeddings.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- users ---------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- documents ------------------------------------------------------------
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("extension", sa.String(16), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False, server_default=sa.text("'unknown'")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'uploaded'")),
        sa.Column("review_status", sa.String(32), nullable=False, server_default=sa.text("'not_required'")),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_scanned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("text_method", sa.String(32), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("summary_is_generated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("processing_meta", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_document_type", "documents", ["document_type"])

    # --- document_pages ---------------------------------------------------------
    op.create_table(
        "document_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("ocr_text", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("section", sa.String(256), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ocr_confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("preview_key", sa.String(512), nullable=True),
        sa.UniqueConstraint("document_id", "page_number", name="uq_page_doc_num"),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])

    # --- document_chunks (includes pgvector embedding) -----------------------------
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(256), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("embedding", sa.Text(), nullable=True),  # replaced by VECTOR below
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunk_doc_index"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_user_id", "document_chunks", ["user_id"])
    # Convert the TEXT placeholder to a real pgvector column.
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE VECTOR(1536) USING embedding::vector")
    # HNSW index for fast cosine similarity search on owned chunks.
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # --- document_entities -----------------------------------------------------------
    op.create_table(
        "document_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("occurrences", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.create_index("ix_document_entities_document_id", "document_entities", ["document_id"])
    op.create_index("ix_document_entities_entity_type", "document_entities", ["entity_type"])

    # --- document_tables ----------------------------------------------------------------
    op.create_table(
        "document_tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("table_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("headers", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("rows", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("source", sa.String(32), nullable=True),
    )
    op.create_index("ix_document_tables_document_id", "document_tables", ["document_id"])

    # --- extraction_results ---------------------------------------------------------------
    op.create_table(
        "extraction_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("schema_type", sa.String(64), nullable=False),
        sa.Column("raw_data", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("corrected_data", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("review_status", sa.String(32), nullable=False, server_default=sa.text("'not_required'")),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("corrections", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("source_refs", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("document_id", "schema_type", name="uq_extraction_doc_schema"),
    )
    op.create_index("ix_extraction_results_document_id", "extraction_results", ["document_id"])

    # --- processing_jobs ------------------------------------------------------------------
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("current_stage", sa.String(32), nullable=True),
        sa.Column("stages", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_processing_jobs_document_id", "processing_jobs", ["document_id"])
    op.create_index("ix_processing_jobs_user_id", "processing_jobs", ["user_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])

    # --- conversations / messages / citations ----------------------------------------------
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "citations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("document_filename", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_citations_message_id", "citations", ["message_id"])

    # --- audit_logs ---------------------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("detail", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("citations")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("audit_logs")
    op.drop_table("processing_jobs")
    op.drop_table("extraction_results")
    op.drop_table("document_tables")
    op.drop_table("document_entities")
    op.drop_table("document_chunks")
    op.drop_table("document_pages")
    op.drop_table("documents")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
