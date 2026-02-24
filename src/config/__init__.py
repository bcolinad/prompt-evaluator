"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    """Application settings with env var support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"

    # LLM — Provider selection (google tries first, anthropic is fallback)
    llm_provider: LLMProvider = LLMProvider.GOOGLE

    # LLM — Google Vertex AI (primary)
    google_model: str = "gemini-2.5-flash"
    google_project: str = "example-project-1"
    google_location: str = "us-central1"
    google_thinking_budget: int = Field(
        default=2048,
        description="Thinking token budget for Gemini 2.5 thinking models. "
        "Set to 0 to disable thinking, -1 for dynamic.",
    )

    # LLM — Anthropic (fallback)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"

    # LLM — Shared
    llm_temperature: float = Field(default=0.0, ge=0.0, le=0.0)
    llm_max_tokens: int = Field(default=16384, gt=0)
    llm_request_timeout: float = Field(
        default=120.0,
        description="Request timeout in seconds for LLM API calls.",
    )

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str | None = None
    langchain_project: str | None = None

    # Database
    database_url: str | None = None

    # LLM — Ollama (self-hosted fallback)
    ollama_chat_model: str = "qwen3:4b"
    ollama_num_predict: int = 16384
    ollama_request_timeout: float = 120.0

    # Embeddings (Ollama — self-hosted, free)
    ollama_base_url: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    similarity_threshold: float | None = None
    max_similar_results: int | None = None

    # Evaluation pipeline
    default_execution_count: int = Field(
        default=2,
        ge=2,
        le=5,
        description="Number of times to execute each prompt for reliability (2-5).",
    )

    # Document processing
    doc_max_file_size: int = Field(
        default=100 * 1024 * 1024,
        description="Maximum document file size in bytes (default 100MB).",
    )
    doc_chunk_size: int = Field(
        default=2000,
        description="Character size for document chunks (larger = fewer chunks, more context per chunk).",
    )
    doc_chunk_overlap: int = Field(
        default=400,
        description="Overlap between document chunks in characters (prevents cutting sentences).",
    )
    doc_max_chunks_per_query: int = Field(
        default=15,
        description="Maximum number of document chunks to retrieve per RAG query.",
    )
    doc_enable_extraction: bool = Field(
        default=True,
        description="Enable LangExtract structured entity extraction from documents.",
    )
    doc_extraction_model: str = Field(
        default="gemini-2.5-flash",
        description="LLM model to use for LangExtract entity extraction.",
    )

    # PDF OCR fallback
    pdf_ocr_enabled: bool = Field(
        default=True,
        description="Enable tiered OCR fallback for scanned/image-based PDFs.",
    )
    pdf_ocr_min_text_chars: int = Field(
        default=50,
        description="Minimum extracted text characters before triggering OCR fallback.",
    )

    # Auth
    auth_enabled: bool = True
    auth_secret_key: str | None = None
    auth_admin_email: str | None = None
    auth_admin_password: str | None = None

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT

    @property
    def async_database_url(self) -> str:
        """Convert plain URL to async for SQLAlchemy asyncpg."""
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is not configured. Set it in your .env file.\n"
                "Example: DATABASE_URL=postgresql://user:pass@localhost:5432/prompt_evaluator"
            )
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    @property
    def sync_database_url(self) -> str:
        """Plain PostgreSQL URL for Alembic and asyncpg."""
        if not self.database_url:
            raise ValueError("DATABASE_URL is not configured. Set it in your .env file.")
        return self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        The singleton Settings loaded from environment / .env file.
        Cached after the first call via ``lru_cache``.

    Side effect:
        Propagates LangSmith env vars into ``os.environ`` so that the
        LangChain/LangSmith SDK (which reads ``os.environ`` directly)
        picks them up even when values originate from a ``.env`` file.
    """
    settings = Settings()

    # LangChain/LangSmith SDK reads these directly from os.environ.
    # pydantic-settings loads them from .env but doesn't write them back,
    # so we propagate them here.
    os.environ.setdefault("LANGCHAIN_TRACING_V2", str(settings.langchain_tracing_v2).lower())
    if settings.langchain_api_key:
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
    if settings.langchain_project:
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)

    return settings
